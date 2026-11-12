# Bundled Windows GCC

The Windows installer includes the GCC toolchain staged at `resources/gcc/ucrt64`. Build from Windows with MSYS2 UCRT64 GCC and binutils installed in `C:\msys64\ucrt64`; the Tauri pre-build step copies that prefix here and packages it as an application resource. Students do not need a separate GCC installation.

To use a different MSYS2 prefix, set `GEETA_GCC_BUNDLE_SOURCE` before building. The full prefix is copied so the compiler retains its linker, assembler, headers, libraries, runtime DLLs, and bundled license files. The native runner selects this packaged compiler and adds its `bin` directory to `PATH` when compiling and running student programs. `GEETA_GCC_PATH` remains available as a developer override.
