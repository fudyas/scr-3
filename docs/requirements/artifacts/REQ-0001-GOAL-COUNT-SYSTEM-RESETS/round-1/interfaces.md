# Revision 8 interfaces

- Module owns boot guard, immutable pending record identity, retry, count, filter, reset, serialization.
- Bash frontend transports module requests only.
- SysV activation follows verified Debian 8 default runlevel `2`.
- Package removal handles loaded and absent module, deletes only validated generated records, restores baseline.
- Toolchain compiler/binutils run only through `./bin/lets toolchain`.
- Image mutation runs only inside one `./bin/lets sdlc lock-run` or `test-package` lock.
