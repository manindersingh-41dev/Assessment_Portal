# GCC installation

The Windows installer does not include GCC. Install a Windows x64 GCC toolchain on each laptop and add its `bin` directory to `PATH`.

If GCC is installed outside `PATH`, set `GEETA_GCC_PATH` to the full path of `gcc.exe` before launching the app. The runner reports the detected compiler version before execution.
