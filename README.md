# PyHookV
A python wrapper for ScriptHookV.  
This allows you to call native GTA V functions using python.

This wrapper implements a subset of all GTA V functions.  
A full list of native functions with *some* documentation can be found [here](http://www.dev-c.com/nativedb/).  

## Building instructions
Make sure to fetch all submodules in git `git submodule update --init --recursive` and download the scripthook SDK.  
Also copy the scripthook DLL into the game directory.

You will need Microsoft Visual Studio for compilation.  
Open `pyhookv.sln` and build with the `Release x64` configuration.

After this is done, copy `pyhookv.pyd` into the GTA V game directory (where GTA5.exe) lives.

Now, [GameHook](https://github.com/philkr/gamehook)'s python plugin `python.hk` will allow you to call scripthook commands in python.

For an example script see `examples/`.

## Adding custom functions
Most of the code of this plugin (`enums.cpp`, `natives.cpp`, `native_type.h`) is automatically generated from ScriptHookV using `gen.py`.  
If you wish to change some wrapped functions define them in `custom.cpp` and rerun the generator.   
The generator automatically ignores functions that are wrapped in `custom.cpp`.
