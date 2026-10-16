"""Regenerate vnpy bindings against the bundled macOS SDK in a build copy only."""
from pathlib import Path
import re
import subprocess
import sys


def prepare(source: Path) -> None:
    source = source.resolve()
    if 'raw' in source.parts:
        raise ValueError('Refusing to modify a raw snapshot')
    api = source / 'vnpy_ctp/api'
    gen = api / 'generator'
    # The upstream generators read UTF-8; vendor macOS headers are GB18030.
    for header in (api / 'include/mac/ctp').glob('*.h'):
        raw = header.read_bytes()
        try:
            raw.decode('utf-8')
        except UnicodeDecodeError:
            header.write_text(raw.decode('gb18030'), encoding='utf-8')
    for name in ('generate_data_type.py', 'generate_struct.py', 'generate_api_functions.py'):
        path = gen / name
        path.write_text(path.read_text().replace('../include/ctp/', '../include/mac/ctp/'))
        if name == 'generate_struct.py':
            path.write_text(path.read_text().replace('line.split("\\t")', 'line.split()'))
        subprocess.run([sys.executable, '-B', str(path)], cwd=gen, check=True)
    for kind, cls, vendor in [('md', 'MdApi', 'Md'), ('td', 'TdApi', 'Trader')]:
        base = api / f'vnctp/vnctp{kind}/vnctp{kind}'
        original_h = base.with_suffix('.h').read_text()
        original_cpp = base.with_suffix('.cpp').read_text()
        fragment = lambda part: (gen / f'ctp_{kind}_{part}').read_text()
        names = ['createFtdc' + vendor + 'Api', 'release', 'init', 'join', 'exit',
                 'getTradingDay', 'getApiVersion', 'registerFront', 'registerNameServer']
        names += ['subscribeMarketData', 'unSubscribeMarketData'] if kind == 'md' else ['subscribePrivateTopic', 'subscribePublicTopic']
        methods = []
        declarations = []
        for name in names:
            matches = re.findall(rf'^(?:void|int|string) {cls}::{name}\([^\n]*\)\n\{{.*?^\}};', original_cpp, re.M | re.S)
            if not matches:
                raise ValueError(f'Missing lifecycle method {name}')
            for method in matches:
                declarations.append(method.split('\n')[0].replace(cls + '::', '') + ';')
                methods.append(method)
        lifecycle = '\n'.join(methods).replace(', false, false, bIsProductionMode)', ', false, false)').replace('(pszFlowPath.c_str(), bIsProductionMode)', '(pszFlowPath.c_str())')
        callbacks = re.findall(r'^void ' + cls + r'::(On[^\n]+)\n', fragment('source_task.cpp'), re.M)
        prefix = original_h[:original_h.index('//常量')]
        class_start = original_h[original_h.index('class ' + cls):original_h.index('virtual void OnFrontConnected')]
        base.with_suffix('.h').write_text(prefix + fragment('header_define.h') + '\n' + class_start + '\n' + '\n'.join('virtual void ' + c + ';' for c in callbacks) + '\nvoid processTask();\n' + fragment('header_process.h') + fragment('header_on.h') + '\n'.join(declarations) + '\n' + fragment('header_function.h') + '\n};\n')
        worker = f'''void {cls}::processTask() {{
    try {{ while (this->active) {{
        Task task = this->task_queue.pop();
        switch (task.task_name) {{ {fragment('source_switch.cpp')} }}
    }} }} catch (const TerminatedError&) {{}}
}};
'''
        req = fragment('source_function.cpp')
        if kind == 'td':
            req = req.replace('ReqUserLogin(&myreq, reqid)', 'ReqUserLogin(&myreq, reqid, 2, "vn")')
        binding = f'PYBIND11_MODULE(vnctp{kind}, m) {{\nclass_<{cls}, Py{cls}> binding(m, "{cls}", module_local());\nbinding.def(init<>())\n'
        for name in names:
            if name == 'subscribeMarketData':
                binding += f'.def("{name}", static_cast<int ({cls}::*)(string)>(&{cls}::{name}))\n'
            else:
                guard = ', call_guard<gil_scoped_release>()' if name in ('release', 'init', 'join', 'exit') else ''
                binding += f'.def("{name}", &{cls}::{name}{guard})\n'
        binding += fragment('source_module.cpp') + '\n}\n'
        base.with_suffix('.cpp').write_text(f'#include "vnctp{kind}.h"\n' + fragment('source_task.cpp') + worker + fragment('source_process.cpp') + lifecycle + '\n' + req + f'\nclass Py{cls}: public {cls} {{ public:\n' + fragment('source_on.cpp') + '\n};\n' + binding)
    meson = source / 'meson.build'
    text = meson.read_text().replace("'-std=c++11'", "'-std=c++17'").replace('10.12', '11.0')
    for library in ('thostmduserapi', 'thosttraderapi'):
        text = text.replace("dependencies: [py_dep],\n  cpp_args",
                            f"dependencies: [py_dep, {library}_lib],\n  cpp_args", 1)
        old = ("extra_link_args + [\n    '-L' + lib_dir,\n    '-l" + library
               + "_se',\n    '-Wl,-rpath,$ORIGIN'\n  ]")
        text = text.replace(old, 'extra_link_args')
    text = text.replace("install_rpath: '$ORIGIN'", "install_rpath: '@loader_path'")
    meson.write_text(text)


if __name__ == '__main__':
    prepare(Path(sys.argv[1]))
