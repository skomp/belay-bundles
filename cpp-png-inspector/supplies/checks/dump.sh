#!/usr/bin/env bash
# usage: dump.sh basic|text|badcrc|truncated
#
# Runs your inspector over one of the supplied PNGs and checks what it reported.
# It reads only the line shapes COURSE.md fixes; the rest of your output is yours.

. "$(dirname "$0")/_lib.sh"

case "${1:-}" in
  basic|text|badcrc|truncated) which="$1" ;;
  *) die "usage: dump.sh basic|text|badcrc|truncated" ;;
esac

bin="$(find_pngdump)"
asset="$root/assets/$which.png"
[ -f "$asset" ] || die "missing asset $asset — it is supplied by the course and should not have been deleted"

out="$("$bin" "$asset" 2>&1)"; status=$?

[ "$status" -lt 128 ] || die "pngdump died on a signal (exit $status) reading $which.png.
      Reporting a malformed file is the job; crashing on it is not."

case "$which" in
  basic|text)
    [ "$status" -eq 0 ] || die "pngdump exited $status on a valid PNG. Its output was:
$out"
    got="$(printf '%s\n' "$out" | chunk_lines)"
    want="$(cat "$expected/$which.chunks")"
    if [ "$got" != "$(printf '%s' "$want")" ]; then
      die "the chunk listing for $which.png is not what the file contains.

expected (offset type length, one per chunk, in file order):
$want
got:
${got:-<no line matched '<offset> <type> <length>'>}"
    fi
    errs="$(printf '%s\n' "$out" | error_lines)"
    [ -z "$errs" ] || die "pngdump reported a problem in a valid PNG:
$errs"
    if [ "$which" = text ]; then
      printf '%s\n' "$out" | grep -q 'Software' \
        || die "the tEXt chunk's keyword 'Software' does not appear in the output.
      The chunk is listed, so it is being walked past rather than read."
      printf '%s\n' "$out" | grep -q 'Belay course asset' \
        || die "the tEXt chunk's value does not appear in the output.
      Note the value is NOT null-terminated: it runs to the end of the chunk."
    fi
    echo "ok: $which.png listed correctly"
    ;;
  badcrc)
    errs="$(printf '%s\n' "$out" | error_lines)"
    [ -n "$errs" ] || die "badcrc.png has a deliberately wrong CRC on its IHDR chunk and
      pngdump reported nothing. Its output was:
$out"
    printf '%s\n' "$errs" | grep -qi 'crc' \
      || die "a problem was reported but it does not mention the CRC:
$errs"
    [ "$status" -ne 0 ] || die "the bad CRC was reported but pngdump still exited 0.
      A tool that found a problem should say so in its exit status."
    echo "ok: bad CRC reported — $errs"
    ;;
  truncated)
    errs="$(printf '%s\n' "$out" | error_lines)"
    [ -n "$errs" ] || die "truncated.png ends part-way through its IDAT chunk and
      pngdump reported nothing. Its output was:
$out"
    [ "$status" -ne 0 ] || die "the truncation was reported but pngdump still exited 0."
    printf '%s\n' "$out" | chunk_lines | grep -q '^8 IHDR 13$' \
      || die "the chunks before the truncation should still be listed.
      A parser that gives up on the whole file because its last chunk is short
      throws away everything it had already read correctly."
    echo "ok: truncation reported — $errs"
    ;;
esac
