# Environment Notes

## Platform: Windows + Git Bash

The host OS is **Windows**, but the shell is configured as **bash** (Git Bash). This creates a hybrid environment where most Unix commands work, but there are important differences to be aware of.

## Path Conventions

- Windows native paths use backslashes: `C:\Users\username\project`
- Git Bash paths use forward slashes: `/c/Users/username/project`
- When passing paths to bash commands, prefer forward-slash format or quote the path
- Windows filesystem is **case-insensitive** but **case-preserving** — avoid relying on case-sensitive path distinctions
- Avoid paths with spaces without quoting; prefer double quotes around paths

## Command Behavior Differences

- `sed`, `awk`, `grep`, `find` etc. are available via Git Bash but may have subtle behavioral differences from GNU/Linux versions
- `which` works in Git Bash; `where` is the native Windows equivalent
- `open` does not exist; use `explorer .` to open a folder in File Explorer, or `start` to open files with default programs
- `pbcopy`/`pbpaste` do not exist; use `clip` and `powershell Get-Clipboard` as alternatives
- `realpath` may not be available; use `readlink -f` or `cygpath -w`/`cygpath -u` for path conversion
- Symbolic links require elevated privileges or Developer Mode enabled; prefer junctions or copies

## Line Endings

- Windows uses CRLF (`\r\n`); Git Bash tools typically output LF (`\n`)
- Git may auto-convert line endings depending on `core.autocrlf` setting
- When editing files, be mindful of mixed line endings

## Process & System Commands

- `ps` in Git Bash shows MSYS2 processes only; use `tasklist` for all Windows processes
- `kill` works for Git Bash processes; use `taskkill /PID <pid> /F` for Windows processes
- Environment variables: in bash use `$VAR` or `${VAR}`, not `%VAR%`
- `echo $PATH` shows bash-style colon-separated paths, not Windows semicolon-separated

## Networking

- `curl` and `ssh` are available via Git Bash
- `netstat`, `ping`, `nslookup` work from both Git Bash and CMD

## File Permissions

- Unix-style `chmod` has limited effect on NTFS; execute permission is determined by file extension (`.exe`, `.bat`, `.cmd`, `.ps1`)
- `chmod +x` on a script without a Windows extension won't make it executable in CMD/PowerShell

## Node.js / npm

- Use `npx` and `npm` from Git Bash as usual
- If Node scripts spawn child processes, they may use CMD by default unless explicitly configured

## Python

- If using Python, prefer `uv run` for virtual environment management as configured
- `python` or `python3` may point to the Windows Python or the Git Bash Python depending on PATH order

## 执行约束原则

1. **严格步骤执行** — 执行 skill 时，必须严格遵循其定义的 phase/step 顺序，不得跳过、合并、调序或提前执行后续步骤。

2. **单步完成制** — 同一时间仅执行一个步骤，完成该步并自我验证通过后，才允许进入下一步。

3. **如无必要勿增实体** — 不创建任务未要求的文件、抽象层、依赖或功能。仅实现明确指定的内容，不做过度设计。

4. **使用中文** — 所有输出、交流、审查记录、日志及代码注释均使用中文。用户的母语是中文，全程保持中文交流。
