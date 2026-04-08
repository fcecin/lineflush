# lineflush

Run commands with colors, animations, and clean log output.

## The problem

Many build tools use animated terminal spinners that overwrite previous lines using cursor-up escape sequences. This can destroy important output like test summaries.

The usual workarounds have tradeoffs:

- **`tee`** preserves output but loses colors (programs detect the pipe and disable them)
- **`unbuffer | tee`** restores colors but the spinner damage is preserved in the log, and the spinner can still overwrite important output

## The solution

`lineflush` wraps your command in a pseudo-terminal so it emits colors and animations normally. It monitors the byte stream and detects when a cursor-up sequence would overwrite unrelated content (like a spinner eating a test summary). When this happens, the cursor-up is suppressed and any trailing spinner remnants are dropped at EOF.

The result: colors and animations work on your terminal, the log file is clean, and important output survives.

## How it works

When a cursor-up escape sequence arrives, lineflush compares the two most recently completed lines. If they differ by 5 or fewer characters (after stripping ANSI codes), they're part of an in-place animation and the cursor-up is allowed. If they differ by more, the cursor-up would overwrite unrelated content and is suppressed.

When a cursor-up is suppressed, output enters "hold" mode. Held output is buffered and only released when real content resumes (detected structurally: two consecutive newlines without an intervening cursor-up). At EOF, any held spinner remnants are silently dropped.

Log output has destructive sequences (cursor-up, erase-line, carriage-return) stripped, but ANSI color codes are preserved.

## Install

```bash
git clone https://github.com/fcecin/lineflush.git
cp lineflush/lineflush /usr/local/bin/
# or
cp lineflush/lineflush ~/bin/
```

Requires Python 3.6+ (uses only the standard library).

Linux only (`pty` module).

## Usage

```bash
# Run a command with colors preserved
lineflush make build

# Run with environment variables
lineflush env POSTGRES=1 make test

# Log output to a file (replaces unbuffer + tee)
lineflush -o build.log make build

# Adjust spinner detection threshold (default: 5 chars)
lineflush -t 10 make test
```

### Options

```text
-o, --output LOGFILE   Write clean output to a log file
-t, --threshold N      Character diff threshold for spinner detection (default: 5)
--version              Show version
```

### Exit code

lineflush exits with the same exit code as the wrapped command.

## Tests

```bash
python3 test_lineflush.py -v
```

## Samples

The `samples/` directory contains build and test scripts for [Logos Delivery](https://github.com/logos-messaging/logos-delivery) (a Nim project using nimble and make) that demonstrate real-world lineflush usage. See [samples/README.md](samples/README.md) for details.

## License

Unlicense (public domain)
