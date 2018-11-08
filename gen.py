import re


# Change these variables to only generate a subset of the files
GEN_ENUMS = True
GEN_NATIVES = True

REGEX_STRIP_COMMENTS = re.compile(r'//.*?$|/\*.*?\*/', re.DOTALL | re.MULTILINE)
REGEX_CAMEL_TO_UNDERSCORE_R1 = re.compile(r'(.)([A-Z][a-z]+)')
REGEX_CAMEL_TO_UNDERSCORE_R2 = re.compile(r'([a-z0-9])([A-Z])')
REGEX_ENUM = re.compile('enum\W+(\w+)[^{]*\{([^}]*)\};', flags=re.DOTALL | re.MULTILINE)

AUTOGEN_HEADER = '''// This file is auto-generated, do NOT edit!
#include "pybind11/pybind11.h"
#include "scripthook/enums.h"

namespace py = pybind11;
'''


def write_to_path(path, source_code):
    with open(path, 'w') as f:
        f.write(source_code)


def read_and_strip_comments(path):
    with open(path, 'r') as f:
        return strip_comments(f.read())


def strip_comments(s):
    return REGEX_STRIP_COMMENTS.sub(' ', s)


def convert_camel_to_underscore(r):
    s = REGEX_CAMEL_TO_UNDERSCORE_R1.sub(r'\1_\2', r)
    t = REGEX_CAMEL_TO_UNDERSCORE_R2.sub(r'\1_\2', s).lower()
    return t


def gen_enums():
    enum_header_code = read_and_strip_comments('dependencies/scripthook/enums.h')

    source_code = [AUTOGEN_HEADER]
    source_code.append('void defEnums(py::module m) {')

    for name, vals in REGEX_ENUM.findall(enum_header_code):
        source_code.append('\tpy::enum_<%s>(m, "%s")' % (name, name))

        for enum in map(lambda x: x.strip(), vals.split(',')):
            if not enum:
                continue
            elif '=' in enum:
                enum = enum[:enum.find('=')].strip()

            source_code.append(
                    '\t\t.value("%s",%s::%s)' % (
                        convert_camel_to_underscore(enum.replace(name, '')), name, enum))
        source_code.append(';')
    source_code.append('}')

    write_to_path('src/enums.cpp', '\n'.join(source_code))


if GEN_ENUMS:
    print("************** Parsing enums **************")

    gen_enums()

from collections import OrderedDict
types = OrderedDict()
types['Void'] = ('DWORD', None)
types['Any'] = ('DWORD', None)
types['uint'] = ('DWORD', None)
types['Hash'] = ('DWORD', None)
types['Entity'] = ('int', 'Any')
types['Player'] = ('int', 'Any')
# types['FireId'] = ('int', None) # Unused in ScriptHookV
types['Ped'] = ('int', 'Entity')
types['Vehicle'] = ('int', 'Entity')
types['Cam'] = ('int', 'Any')
# types['Group'] = ('int', None) # Unused in ScriptHookV
# types['Train'] = ('int', None) # SH uses vehicle instead
types['Object'] = ('int', 'Entity')
types['Pickup'] = ('int', 'Object')
# types['Weapon'] = ('int', None) # Unused in ScriptHookV
# types['Interior'] = ('int', None) # Unused in ScriptHookV
types['Blip'] = ('int', 'Any')
# types['Texture'] = ('int', None) # Unused in ScriptHookV
# types['TextureDict'] = ('int', None) # Unused in ScriptHookV
# types['CoverPoint'] = ('int', None) # Unused in ScriptHookV
# types['Camera'] = ('int', None) # Unused in ScriptHookV
# types['TaskSequence'] = ('int', None) # Unused in ScriptHookV
# types['ColourIndex'] = ('int', None) # Unused in ScriptHookV
# types['Sphere'] = ('int', None) # Unused in ScriptHookV
types['ScrHandle'] = ('int', None)

type_def = OrderedDict()
type_def['Hash'] = '.def(py::init<DWORD>())'

accepted_types = {'char*', 'BOOL', 'int', 'float'}
accepted_ret_typed = {'void', 'Vector3'} | accepted_types

def map_ret(tp):
    # TODO: Wrap the type
    if tp in types:
        return 'Py_'+tp
    assert tp in accepted_ret_typed, "Unknown type '%s'!"%tp
    return tp

def map_type(tp, vn):
    # TODO: Wrap the type
    if tp in types:
        return 'Py_'+tp+' '+vn, vn+'.id'
    assert tp in accepted_types, "Unknown type '%s'!"%tp
    return tp+' '+vn, vn

def wrap(fn, rt, params, force_type=None):
    if force_type is not None and len(params) and '*' not in params[0][0]: params[0] = (force_type, params[0][1])
    dcl, cl = '', ''
    if len(params):
        dcl, cl = zip(*[map_type(*p) for p in params])
    return '[](%s) -> %s { return %s(%s); }'%(','.join(dcl), map_ret(rt), fn, ','.join(cl))

print( "************** Parsing natives ************** " )
custom_r = re.compile(r'([A-Z]+\:\:[A-Z_0-9]+)')
with open('src/custom.cpp', 'r') as f:
    all_custom = custom_r.findall(f.read())
    all_custom = set(all_custom)

with open('dependencies/scripthook/natives.h', 'r') as f:
    src = strip_comments(f.read())

ns_r = re.compile(r'(\w+)[^{]\{(.*)\}', re.DOTALL | re.MULTILINE)
fn_r = re.compile(r'static\W+(\S+)\s+(\w+)\s*\((.*)\)\W*{')
pr_r = re.compile(r'(.*)\s+(\w+)')
namespaces = []
failed_natives = []
for ns in src.split('namespace')[1:]:
    m = ns_r.match(ns.strip())
    if not m:
        print( "Failed to parse NS" )
        continue
    name, df = m.groups()
    type_name = name[0] + name[1:].lower()

    n_static, n_dynamic, n_skip = 0, 0, 0
    getters, setters = {}, {}
    members, statics = {}, {}

    # Parse all functions
    for rt, fn, args in fn_r.findall(df):
        if 'set_control' in fn.lower():               # TODO(bradyz): Hack.
            pass
        elif fn[:3] == "_0x":                         # Skip hex functions
            continue
        elif name+'::'+fn in all_custom:              # Skip custom functions
            continue
        params = [tuple(i.strip() for i in pr_r.match(p.strip()).groups()) for p in args.split(',') if p.strip()]
        is_member = len(params) > 0 and (params[0][0] == type_name or params[0][1] == type_name.lower()) and type_name in types
        s_fn = fn.lower()

        ns_fn = name+'::'+fn
        if s_fn[0] == '_': s_fn = s_fn[1:]
#       if is_member:
        s_fn = s_fn.replace(type_name.lower()+'_', '')
        if len(params) == 1 and is_member and (s_fn[:4] == "get_" or s_fn[:3] == "is_" or s_fn[:4] == "are_" or s_fn[:4] == "can_"):
            s_fn = s_fn.lower().replace('get_', '')
            getters[s_fn] = (ns_fn, rt, params)
        elif len(params) == 2 and s_fn[:4] == "set_" and is_member:
            s_fn = s_fn.lower().replace('set_', '')
            setters[s_fn] = (ns_fn, rt, params)
        elif is_member:
            members[s_fn] = (ns_fn, rt, params)
        else:
            statics[s_fn] = (ns_fn, rt, params)

    # Create the definitions
    code = ''
    for g in sorted(getters):
        if g in setters:
            code += '\t\t.def_property("%s", %s, %s)\n'%(g, wrap(*getters[g], force_type=type_name), wrap(*setters[g], force_type=type_name))
            del setters[g]
        else:
            code += '\t\t.def_property_readonly("%s", %s)\n'%(g, wrap(*getters[g], force_type=type_name))
    for g in sorted(setters):
        try:
            code += '\t\t.def("set_%s", %s)\n'%(g, wrap(*setters[g], force_type=type_name))
        except AssertionError:
            failed_natives.append(setters[g][0])
    for g in sorted(members):
        try:
            code += '\t\t.def("%s", %s)\n'%(g, wrap(*members[g], force_type=type_name))
        except AssertionError:
            failed_natives.append(members[g][0])
    for g in sorted(statics):
        try:
            code += '\t\t.def_static("%s", %s)\n'%(g, wrap(*statics[g]))
        except AssertionError:
            failed_natives.append(statics[g][0])

    if type_name in type_def:
        type_def[type_name] += code
    else:
        type_def[type_name] = code
    print( '-', name, type_name, ' #S:', len(statics), ' #M:', len(members), ' #G:', len(getters), ' #SET:', len(setters) )

empty_types = [t for t in type_def if t not in types]

with open('failed_natives.txt', 'w') as f:
    f.write('\n'.join(failed_natives))

if GEN_NATIVES:
    with open('src/natives_type.h', 'w') as f:
        print('// This file is auto-generated, do NOT edit!', file=f)
        print('#include "scripthook/types.h"', file=f)
        
        for t in types:
            T, inh = types[t]
            I,D,B = '', '', 'id'
            if inh is not None:
                I = ':Py_'+inh
                B = 'Py_'+inh
            else:
                D = '\t'+T+' id=0;'
            
            def P(s): print(s.replace('{T}', t).replace('{B}', B).replace('{I}', I), file=f)
            P('struct Py_{T}{I}{')
            P(D)
            P('\tPy_{T}(int i): {B}(i){}')
            P('\tPy_{T}(DWORD i): {B}(i){}')
            P('\tPy_{T}&operator=(int i) { id = i; return *this; }')
            P('\tPy_{T}&operator=(DWORD i) { id = i; return *this; }')
            P('\toperator int() { return id; }')
            P('\toperator DWORD() { return id; }')
            P('};')
        
        for t in empty_types:
            print('struct Py_'+t+'{};', file=f)
    
    with open('src/natives.cpp', 'w') as f:
        print('// This file is auto-generated, do NOT edit!', file=f)
        print('#include "pybind11/pybind11.h"', file=f)
        print('#include "scripthook/natives.h"', file=f)
        print('#include "natives_type.h"', file=f)
        print('namespace py = pybind11;', file=f)
        
        print('void defNatives(py::module m) {', file=f)
        # Lovely C++11
        print('\tpy::class_<Vector3>(m, "Vector3").def("__init__", [](Vector3 &self, float x, float y, float z) {new (&self) Vector3{ x, 0, y, 0, z, 0 }; }).def_readwrite("x", &Vector3::x).def_readwrite("y", &Vector3::y).def_readwrite("z", &Vector3::z);', file=f)
        # Forward declare all custom functions
        for t in sorted(list(types)+list(empty_types)):
            def P(s): print(s.replace('{T}', t), file=f)
            P('void custom(py::class_<Py_{T}>);')
        

        # Handle all typed namespaces
        for t in types:
            T, inh = types[t]
            I,df = '', ''
            if t in type_def: df = type_def[t]
            if inh is not None: I = ',py_'+inh
            def P(s): print(s.replace('{T}', t).replace('{I}', I).replace('{df}', df), file=f)
            P('\tpy::class_<Py_{T}> py_{T}(m, "{T}"{I});')
            P('\tpy_{T}.def("__bool__", [](Py_{T} t){return (BOOL)t.id;});')
            P('\tpy_{T}')
            P('{df};')
            P('\tcustom(py_{T});')
        # Handle all non-type namespaces
        for t in empty_types:
            df = ''
            if t in type_def: df = type_def[t]
            def P(s): print(s.replace('{T}', t).replace('{df}', df), file=f)
            P('\tpy::class_<Py_{T}> py_{T}(m, "{T}");')
            P('\tpy_{T}')
            P('{df};')
            P('\tcustom(py_{T});')
        print('}', file=f)
        print('', file=f)
