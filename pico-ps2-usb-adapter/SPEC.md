# Build a PS/2 to USB HID Keyboard Adapter on the Raspberry Pi Pico

**Bundle id:** `pico-ps2-usb-adapter`
**Scale:** long
**Status:** approved by the author 2026-09-29, and built. Revised the same day to carry
the course-quality audit's findings; see the revision note at the foot of this file.
**Date:** 2026-09-29

## The learner

For an experienced software engineer who is comfortable with C, pointers, bit
manipulation, git and reading reference documentation, and who does **not** need any
introductory programming instruction — but who has never written microcontroller firmware,
never reasoned about a pull-up resistor, never read a digital signal off a wire, and never
met USB below the level of "plug it in".

The teaching effort goes entirely into the embedded, electrical, timing and protocol
layers. The computer-science content is not simplified: a lock-free single-producer ring
buffer is described as one, not built up from first principles.

At the end they have a soldered adapter in a case that presents an IBM Model M to any
modern computer as an ordinary USB HID keyboard — no driver, working in a BIOS, lock LEDs
lit — and they can explain the whole path, from the open-drain edge on the PS/2 clock line
to the 8-byte interrupt-IN report the host polls for.

**One sentence:** plug a Model M into the box and into any computer, and it just types —
and you can say exactly why, at every layer.

## The arc

Twenty main-path lessons in eight milestones, plus seven offered lessons. Each lesson
ends in something the learner can observe or measure before the next one starts.

The course is deliberately shaped so that the **CPU-interrupt receiver comes before the
PIO receiver**. PIO is a hardware state machine and teaches nothing about ISR latency,
ISR/main-loop shared state, `volatile` or critical sections — all of which the learner is
new to and all of which are named learning goals. Writing the interrupt version first also
means the PIO version is debugged against a known-good reference rather than against an
unfamiliar protocol. The offload comparison in lesson 08 requires something to compare
against. PIO then becomes the real implementation for the rest of the course.

### Main path

| # | slug | purpose | objective | instructive failure | completion | design_refs | validators |
|---|---|---|---|---|---|---|---|
| 00 | `first-code-and-a-window-in` | get your own code running on the chip, and get a way to see inside it that USB cannot later steal | microcontroller execution model; boot ROM, UF2, XIP flash, the memory map; a debug console that is not USB | expecting `printf` to appear with no stdio route enabled; mistaking the BOOTSEL mass-storage bootloader for a running program; putting stdio on USB and losing it in lesson 11 | LED blinks under learner-written code and a line the learner chose appears on the UART console | `#debug-channel`, `#pin-assignment` | `build-ok`, `firmware-alive` |
| 01 | `the-ps2-connector-and-what-is-safe` | identify the four live pins on a Model M's plug and prove the Pico can power it, before any GPIO is connected | mini-DIN-6 pinout; reading a pinout that is drawn from one side; current budget on VBUS; why 5 V on a 3.3 V GPIO is destructive | reading the pinout mirrored (socket view vs plug view — the single most common mistake with this connector); connecting DATA to a GPIO "just to see"; assuming the keyboard's draw without measuring | learner states each pin with multimeter evidence and the measured idle and typing current, with nothing yet wired to a GPIO | `#voltage-domains` | `wiring-verified` |
| 02 | `open-drain-and-pull-ups` | build the interface between a 5 V open-collector bus and a 3.3 V part, and understand why it has to be built that way | push-pull vs open-drain; why open-drain makes a shared bidirectional line possible; pull-up sizing against bus capacitance; bidirectional level shifting | reaching for a resistor divider, which cannot work on a line either end may pull low; a unidirectional buffer, which breaks lesson 09's transmit; a pull-up so weak the rise time eats the edge | both sides idle high at their own rail, either end can pull the line low, and the learner can state the RC estimate for their chosen pull-up | `#voltage-domains`, `#pin-assignment` | `pullups-verified` |
| 03 | `see-the-protocol-before-you-decode-it` | derive the PS/2 frame format from your own capture rather than from a document | logic analyser use: sample rate, threshold, triggering; reading a clocked serial frame off a trace | sampling too slowly and aliasing the clock; sampling data on the wrong clock edge; trusting a web page's frame diagram over the trace in front of you; believing the intra-byte bit order was derived when it was assumed | learner presents a capture of one keypress, reads start, eight data bits, parity and stop out of it, states the measured clock period, and states the intra-byte bit order as a choice with the test that would falsify it | `#wire-format` | `signal-captured` |
| 04 | `your-first-interrupt` | take a hardware event into your code and prove the CPU is reacting to the wire | interrupts and the NVIC; the pico-sdk GPIO IRQ callback; ISR latency; what may not be done inside an ISR | `printf` inside an ISR; arming the interrupt before configuring the pin; not accounting for the interrupt firing on noise; a counter the compiler caches | clock edges counted in an ISR appear as a rising count on the console, eleven per keypress-ish and stable | `#pin-assignment`, `#debug-channel` | `build-ok`, `edges-counted` |
| 05 | `a-state-machine-in-an-isr` | assemble eleven edges into one byte you can trust | framing state machines; shift registers; odd parity; timeout-driven resynchronisation | no idle timeout, so a single glitch desynchronises the receiver permanently; parity computed over the wrong bits; assembling MSB-first; treating a framing error as fatal instead of resyncing | console shows correct, parity-checked bytes for a known key, and still recovers after the learner deliberately glitches the line | `#wire-format` | `build-ok`, `frames-received` |
| 06 | `handing-data-to-the-main-loop` | get bytes out of interrupt context without losing or corrupting them | shared state between an ISR and the main loop; `volatile`; critical sections; a lock-free single-producer single-consumer ring buffer | a non-`volatile` flag optimised away; a ring buffer that races on wrap; masking interrupts long enough to drop a bit; doing the slow work in the ISR because it is easier | a burst of fast typing produces every byte, in order, printed from the main loop, with a drop counter that stays at zero | `#rx-interface`, `#debug-channel` | `build-ok`, `queue-lossless` |
| 07 | `what-a-pio-state-machine-is` | run a program on something that is not the CPU | the PIO ISA and its nine instructions; the four state machines; ISR/OSR shift registers; autopush/autopull; clock dividers; pin mapping and `in` base | wrong clock divider, so the program runs at an unintended rate; confusing the `in` pin base with the pin number; expecting C control flow from an instruction set that has none; forgetting a PIO program keeps running when `main` stops | a PIO program the learner wrote toggles a pin at a rate they predicted, and keeps doing it while the CPU is busy elsewhere | `#pin-assignment` | `build-ok`, `pio-runs` |
| 08 | `ps2-receive-in-pio` | move the framing off the CPU entirely, and measure what that bought | protocol offload; sampling a clocked bus in PIO; autopush thresholds; measuring CPU cost and jitter tolerance | sampling on the wrong clock edge; an autopush threshold that includes or excludes the start and stop bits by mistake; forgetting the word arrives LSB-first and needs reordering after the FIFO; deleting the interrupt backend instead of keeping it as the reference | the same bytes as lesson 06 arrive through the PIO backend, both backends pass the same check, and the learner states the measured difference in CPU time | `#rx-interface`, `#wire-format` | `build-ok`, `pio-frames-received` |
| 09 | `talking-back-in-pio` | drive the bus in the other direction, on a line the device clocks | bus arbitration on a shared open-drain line; the PS/2 host-to-device sequence: inhibit, request-to-send, device-clocked write, the ACK bit; direction changes on one wire | releasing the clock too early in request-to-send, so the device never starts clocking; ignoring the device's ACK bit; not resending on a NAK; holding the bus inhibited so long the keyboard resets | the learner sends `0xFF` (reset), reads `0xFA` then `0xAA` back, and the Model M's LEDs flash its power-on self test | `#wire-format`, `#voltage-domains` | `build-ok`, `keyboard-acks-command` |
| 10 | `scan-codes-to-key-events` | turn a byte stream into key-down and key-up events for every key on your board | scan code set 2; make and break; the `0xF0` break prefix and the `0xE0` extended prefix; the Pause and Print Screen sequences; typematic repeat | treating `0xE0` and `0xF0` as keys in their own right; assuming break equals make with bit 7 set, which is set 1 and not set 2; reading typematic repeat as a stream of new presses; building the table from a web page instead of from your own keyboard | every physical key on the learner's Model M produces one distinct, correctly-named down event and one up event, including Pause and Print Screen | `#wire-format`, `#events-vs-state` | `build-ok`, `key-events-decoded` |
| 11 | `descriptors-you-write-yourself` | answer the questions a host asks a device it has never seen, by writing the answers by hand | the USB device model: bus, addresses, endpoints, transfer types; the enumeration conversation; device, configuration, interface, endpoint and string descriptors | `wTotalLength` that does not match the descriptors that follow; `bInterfaceClass` wrong, so no driver binds and the device enumerates as nothing; a string descriptor with no language-ID descriptor at index 0; an endpoint `bInterval` that contradicts the transfer type | the host enumerates the device with the learner's own VID/PID and strings, and the learner reads their own descriptors back off the host | `#hid-contract` | `build-ok`, `enumerates-as-hid` |
| 12 | `the-hid-report-descriptor` | describe the shape of your reports in a language the host can parse | HID report descriptors as a little stack language: usage pages, usages, logical minimum and maximum, report size and count, input and output items, collections; boot protocol versus report protocol | report size times report count that does not add to the eight bytes you intend; omitting the reserved byte; **declaring the six keys as a bitmap or the modifiers as an array — the central conceptual trap of the whole chapter**; adding a second top-level collection to this interface and silently forcing a report ID, which makes the report nine bytes and breaks boot protocol | the learner reads the report descriptor back off the host, byte for byte as they wrote it, and can walk a parser output item by item | `#hid-contract` | `build-ok`, `report-descriptor-sane` |
| 13 | `your-first-keystroke` | make the host type a character your firmware chose | the interrupt IN endpoint; polling interval; the TinyUSB device task and why it must be serviced; a keypress as two reports, not one | never sending the release report, so one key types forever — memorable, and recoverable only by unplugging; calling the device task nowhere, or blocking inside it; sending a report before the host has configured the device | a character the learner chose appears in a text editor on the host, once per press, and stops | `#hid-contract`, `#failure-posture` | `build-ok`, `keystroke-delivered` |
| 14 | `events-to-state` | join the two halves: PS/2 emits events, USB HID reports state | the key-state model as the single source of truth; building the modifier bitmap and the six-key array from it; sending only on change; 6KRO and the `ErrorRollOver` overflow report | sending one report per PS/2 event, which gives stuck keys the moment two events arrive between polls; putting modifiers in the array; silently dropping the seventh key instead of reporting overflow; blaming the firmware for the Model M's own matrix limits | typing a paragraph produces exactly the right text, no key ever sticks, and pressing seven keys reports overflow rather than losing one silently | `#events-vs-state`, `#hid-contract` | `build-ok`, `no-stuck-keys` |
| 15 | `the-lock-leds` | close the loop: the host tells the keyboard something, and the keyboard obeys | HID output reports and `SET_REPORT`; translating a host LED bitmap into a PS/2 `0xED` command; doing slow work outside a USB callback | handling the OUT report in the wrong callback or on the wrong interface; assuming the HID LED bit order matches PS/2's, which it does not; performing the multi-millisecond PS/2 write inside the USB callback and stalling the endpoint | pressing Caps Lock on the host lights the Caps Lock LED on the Model M, and the state survives a host-side toggle from another keyboard | `#hid-contract`, `#wire-format` | `build-ok`, `leds-follow-host` |
| 16 | `when-it-goes-wrong` | acquire the tools to diagnose the next bug yourself | SWD and gdb through the second Pico; reading a hard fault and finding the faulting instruction; `panic` and the pico-sdk's fault handlers; correlating a logic analyser capture with firmware state by toggling a spare GPIO | debugging by `printf` alone and perturbing the very timing being measured — the Heisenbug this subject is full of; reading a stack trace without knowing which core faulted; assuming a hang is a hang rather than a fault loop | the learner deliberately introduces a fault, catches it in gdb, names the faulting line, and separately correlates a captured edge with a GPIO marker their firmware set | `#debug-channel`, `#pin-assignment` | `build-ok`, `fault-diagnosed` |
| 17 | `robustness-and-the-real-world` | make it behave when things are not ideal | hot-plug and absent-device handling; resynchronisation after a framing or parity error; releasing held keys on error; USB suspend, resume and remote wakeup; the watchdog | assuming the keyboard is present at boot, so the firmware wedges when it is not; latching after one parity error instead of resyncing; leaving a key held when the keyboard is unplugged mid-press; omitting remote wakeup, so the adapter cannot wake the host it is plugged into | the adapter boots with no keyboard attached and picks it up when plugged in, recovers from an induced framing error, never leaves a key held, and wakes a suspended host | `#failure-posture`, `#rx-interface` | `build-ok`, `survives-abuse` |
| 18 | `off-the-breadboard-and-done` | take the circuit off the breadboard and put it in a case you trust | transferring a breadboard circuit to stripboard; track cuts; soldering a connector; strain relief; continuity and isolation testing before first power; staged bring-up | applying power before continuity-testing, and finding the short with the magic smoke; no strain relief, so the first tug lifts a pad; cold joints that work on the bench and fail warm; letting the tutor choose between the level-shifter module and discrete BSS138s, which is the learner's decision | the adapter is soldered, cased and strain-relieved, every cut was verified on the bare board, the bring-up stopped at no surprise, and the console still reports `alive` with the lid on | `#voltage-domains`, `#pin-assignment`, `#deliberately-unresolved` | `build-ok`, `firmware-alive` |
| 19 | `does-it-pass` | turn the brief back into tests, and prove the object is a keyboard | converting a requirement into an acceptance test; boot protocol where it actually matters; re-verifying `#failure-posture` through solder rather than on a breadboard; what a fresh host and a warm hour each catch | declaring victory without testing in a BIOS, where boot protocol is the only thing that saves you; re-running the tests on the machine that has seen every build; trusting a board that was only ever tested cold; reopening the vendor-interface decision instead of confirming it | the finished adapter works from cold boot on a machine that has never seen it, types correctly in the host's firmware setup screen, needs no driver, recovers from a deliberate wedge with the case shut, and survives suspend, resume and replug | `#hid-contract`, `#failure-posture`, `#deliberately-unresolved` | `enumerates-as-hid`, `no-stuck-keys`, `survives-abuse`, `finished-adapter` |

### Offered track

Authored in full, offered by the tutor after the main-path lesson that earns each one.
None is a prerequisite for any main-path lesson.

| slug | purpose | objective | instructive failure | completion | offer after | design_refs | validators |
|---|---|---|---|---|---|---|---|
| `see-the-edges-on-a-scope` | see the rise time you calculated | RC rise time on a real bus; what a logic analyser's threshold hides; why pull-up choice is a trade-off and not a lookup | reading a logic analyser's clean square wave as the truth about the wire; choosing a pull-up from a forum post rather than from the measured capacitance | learner shows traces at two pull-up values and explains the edge each one produces, and which one the receiver can still read | 02 | `#voltage-domains` | `scope-trace-read` |
| `a-safety-catch` | stop buggy firmware typing into whatever has focus | a deliberate enable gate in firmware; failing safe on an input device | a safety catch that fails open on a floating pin; putting the gate after the report is queued rather than before | HID output stays suppressed until the learner grounds the enable pin, verified while a deliberately runaway build is running | 13 | `#failure-posture`, `#pin-assignment` | `build-ok`, `safety-catch-works` |
| `watch-the-enumeration` | see the enumeration conversation as packets rather than infer it from its results | USB transactions on the wire: SETUP, `GET_DESCRIPTOR`, `SET_ADDRESS`, `SET_CONFIGURATION`; reading a pcap of a control transfer | capturing after enumeration and wondering where the descriptors went; on Windows, running a keyboard-bus capture without realising it is literally a keylogger of your own machine | learner presents a capture of their own device enumerating and walks the request sequence | 11 | `#hid-contract` | `enumeration-captured` |
| `a-second-interface-for-debugging` | get a channel through USB itself, and learn why it cannot live on the keyboard interface | composite USB devices; multiple interfaces versus multiple top-level collections; vendor-defined usage pages; why a keyboard collection is reserved by every desktop OS | adding the debug collection to the keyboard interface, which forces a report ID and breaks the eight-byte boot report; expecting to read the keyboard interface's input reports from the host, which no OS permits | the learner reads live device state over a second interface from the host, with the keyboard interface still boot-protocol clean | 13 | `#hid-contract`, `#debug-channel` | `build-ok`, `second-interface-live` |
| `measure-your-latency` | find out what the adapter actually costs the typist | end-to-end latency measurement; instrumenting firmware with a GPIO marker; comparing the two receive backends with numbers | measuring the firmware's internal time and calling it end-to-end latency; comparing backends without holding the host's polling interval constant | learner reports keypress-to-report latency for both backends with the method stated and the polling interval controlled for | 14 | `#rx-interface` | `latency-measured` |
| `nkro-without-a-driver` | report more than six keys, and understand what you give up | a bitmap input report; report protocol versus boot protocol; why a second report descriptor is the usual answer | replacing the boot report instead of adding to it, so the adapter stops working in a BIOS; expecting the Model M's matrix to deliver arbitrary simultaneous keys | more than six simultaneous keys are reported on the host while the boot interface still works in firmware setup | 14 | `#hid-contract` | `build-ok`, `nkro-reports` |
| `remap-and-macros` | make the layout yours | a keymap layer between key events and HID usages; compile-time versus runtime configuration | remapping at the scan-code layer instead of the key-event layer, so extended keys behave differently from the rest; a macro that outruns the host's polling interval | a remapped key and a multi-key macro both work, and the learner states which layer each change belongs in | 15 | `#events-vs-state` | `build-ok`, `keymap-applied` |

## Chapters and milestones

- **M1 — I can run my own code, and see inside it** (00)
- **M2 — the keyboard is safely connected and I have seen its signal** (01–03)
- **M3 — raw frames arrive in my program** (04–06)
- **M4 — PIO does the framing, in both directions** (07–09)
- **M5 — I have key events for every key on the board** (10)
- **M6 — the host says "a keyboard is plugged in", and it types** (11–13)
- **M7 — it is actually a Model M adapter, lock LEDs and all** (14–15)
- **M8 — a finished object I trust** (16–19)

## Teaching stance

```yaml
workspace_kind: new-repository
tutor_owned:   [tutorial/STATE.md, tutorial/DESIGN.md]
learner_owned:
  - src/**
  - include/**
  - pio/**
  - checks/**
  - docs/**
  - captures/**
  - CMakeLists.txt
  - pico_sdk_import.cmake
  - README.md
  - BOM.md
  - device.env
ownership_policy: tutor-must-not-edit-learner-owned
one_task_at_a_time: true
solution_code: on-request-only
advance_on: validated-evidence-only
```

**The validation channel is the debug UART, not the host.** This is the decision that makes
a hardware course checkable, and it is the direct analogue of `orange-pi-network-appliance`
checking live board state over SSH. The firmware emits structured log lines on UART0 to the
second Pico running `debugprobe`; `checks/_console.py` opens that port and reads them. A
ruleset that is written but never loaded must not pass, and firmware that builds but does
not run must not pass either.

It is also forced. Reading a USB keyboard's own HID input reports back from the host is
blocked by every desktop OS — verified 2026-09-29, see *Host tooling constraints* below —
so the host cannot be the source of evidence for anything after lesson 13.

**Validators are the tutor's to run, never the learner's.** A lesson body names the
validator (`frames-received`, `report-descriptor-sane`) and never a runnable command
string, because a copy-pasteable command invites the tutor to hand the run to the learner,
whose result is an assertion rather than evidence. Learner-performed hardware tests — the
multimeter readings, the logic analyser capture, unplugging the keyboard mid-press, the
BIOS test — stay imperative in the lesson; only the validator invocation is withheld. This
follows the correction recorded in `orange-pi-network-appliance/SPEC.md`.

```yaml
validators:
  toolchain-present:      { kind: command, command: [python3, checks/toolchain.py] }
  build-ok:               { kind: command, command: [python3, checks/build.py] }
  firmware-alive:         { kind: command, command: [python3, checks/console.py, alive] }
  edges-counted:          { kind: command, command: [python3, checks/console.py, edges] }
  frames-received:        { kind: command, command: [python3, checks/console.py, frames] }
  queue-lossless:         { kind: command, command: [python3, checks/console.py, queue] }
  pio-runs:               { kind: command, command: [python3, checks/console.py, pio] }
  pio-frames-received:    { kind: command, command: [python3, checks/console.py, pio-frames] }
  keyboard-acks-command:  { kind: command, command: [python3, checks/console.py, ack] }
  key-events-decoded:     { kind: command, command: [python3, checks/console.py, events] }
  no-stuck-keys:          { kind: command, command: [python3, checks/console.py, reports] }
  survives-abuse:         { kind: command, command: [python3, checks/console.py, robustness] }
  safety-catch-works:     { kind: command, command: [python3, checks/console.py, safety] }
  enumerates-as-hid:      { kind: command, command: [python3, checks/usb.py, enumerate] }
  report-descriptor-sane: { kind: command, command: [python3, checks/usb.py, descriptor] }
  second-interface-live:  { kind: command, command: [python3, checks/usb.py, vendor] }
  nkro-reports:           { kind: command, command: [python3, checks/usb.py, nkro] }
  wiring-verified:        { kind: manual }
  pullups-verified:       { kind: manual }
  signal-captured:        { kind: manual }
  keystroke-delivered:    { kind: manual }
  leds-follow-host:       { kind: manual }
  fault-diagnosed:        { kind: manual }
  finished-adapter:       { kind: manual }
  scope-trace-read:       { kind: manual }
  enumeration-captured:   { kind: manual }
  latency-measured:       { kind: manual }
  keymap-applied:         { kind: manual }

setup_validators:
  - name: toolchain-present
    describe: Checks that cmake, the ARM toolchain and the Pico SDK are where the build will look for them, so a failure in lesson 00 is your code and not your environment.
```

`toolchain-present` and not `build-ok` is deliberate: a setup validator runs at
materialization, before the learner has written a line, so a check that tries to *build*
would fail on every fresh instance and report a working bundle as broken.

The eleven `manual` validators are the ones where a human must look at hardware — a
multimeter reading, a captured trace, a lit LED, a soldered board. That is the honest
answer for this subject, not a gap. Every validator that *can* be a command is one.

## Supplied files

| from | to | describe | scope |
|---|---|---|---|
| `supplies/CMakeLists.txt` | `CMakeLists.txt` | A minimal CMake file that finds the SDK and builds one executable. Everything this course teaches about the build - the stdio route, the PIO header, TinyUSB, the backend switch - you add to it yourself | `tutorial.yaml` |
| `supplies/README.md` | `README.md` | README for this firmware repository and how to build and flash it | `tutorial.yaml` |
| `supplies/gitignore` | `.gitignore` | Keeps the build directory and editor droppings out of your history | `tutorial.yaml` |
| `supplies/pico_sdk_import.cmake` | `pico_sdk_import.cmake` | Boilerplate the Pico SDK requires verbatim; nothing in this course changes it | `tutorial.yaml` |
| `supplies/device.env.template` | `device.env` | device.env: which serial port your debug console is on and which VID/PID your device will use — you fill these in during lesson 00 | `tutorial.yaml` |
| `supplies/BOM.md` | `BOM.md` | The shopping list, with the exact part types this course assumes and why each one | `tutorial.yaml` |
| `supplies/PINOUT.md` | `docs/PINOUT.md` | The pin assignment this course uses, and the mini-DIN-6 pinout drawn from both the plug side and the socket side so you cannot read it mirrored | `tutorial.yaml` |
| `supplies/checks-console.py` | `checks/_console.py` | Shared helper the checks use to open your debug console and read its log lines | `tutorial.yaml` |
| `supplies/checks-usb.py` | `checks/_usb.py` | Shared helper the checks use to find your device on the host and read its descriptors, on Linux, macOS and Windows alike | `tutorial.yaml` |
| `supplies/checks-toolchain.py` | `checks/toolchain.py` | The check that confirms cmake, the ARM toolchain and the Pico SDK are installed and findable | `tutorial.yaml` |
| `supplies/checks-build.py` | `checks/build.py` | The check that configures and builds your firmware | `tutorial.yaml` |
| `supplies/checks-console-cli.py` | `checks/console.py` | The checks that read evidence off your debug console | `tutorial.yaml` |
| `supplies/checks-usb-cli.py` | `checks/usb.py` | The checks that read evidence off the host's view of your device | `tutorial.yaml` |
| `lessons/03-see-the-protocol-before-you-decode-it/captures/model-m-keypress.sr` | `captures/model-m-keypress.sr` | A synthesized reference trace of one keypress and its release, protocol-correct but not captured from real hardware, to compare your own trace against — and to work from if your wiring is not ready yet | `03-see-the-protocol-before-you-decode-it` |
| `lessons/09-talking-back-in-pio/ps2-commands.md` | `docs/ps2-commands.md` | The PS/2 host-to-device command and response codes, as a reference table — deriving these from captures would teach you nothing | `09-talking-back-in-pio` |
| `lessons/14-events-to-state/ps2_set2_to_hid.h` | `include/ps2_set2_to_hid.h` | The complete scan code set 2 to HID usage translation table; lesson 10 had you derive a handful yourself, and this is the rest | `14-events-to-state` |
| `lessons/18-off-the-breadboard-and-done/perfboard-layout.md` | `docs/perfboard-layout.md` | A stripboard layout for the circuit you built on the breadboard, so lesson 18 is about soldering and not about drawing | `18-off-the-breadboard-and-done` |

Note the deliberate split on the translation table. Lesson 10 asks the learner to derive
roughly ten entries from their own captures, because that is where the method is learnt;
the remaining hundred-odd entries are transcription, the bundle can ship them, and so it
does — at lesson 14, which is the first lesson that needs the whole table.

The check scripts are supplied rather than assigned for the same reason. Writing a serial
port reader is not what this course teaches, and a validator the learner wrote is a
validator the learner can satisfy by weakening.

**Not supplied, and deliberately so:** every line of firmware. The Pico SDK itself and the
ARM toolchain need the network, so installing them is the learner's work and lesson 00 asks
for it.

**`CMakeLists.txt` was in that list and is not any more.** The original reasoning was that
the CMake file is edited in nearly every lesson — the PIO header, TinyUSB, the backend
switch — so the learner must be able to change it rather than receive it. The
course-quality audit of 2026-09-29 scored the from-scratch write as the course's only toil
site: this is a single-platform course, so the bundle can ship exactly one file, and under
the rubric's shippability test a skeleton the bundle could have shipped is toil.

Both positions are right about different things, and the resolution keeps both. The bundle
now supplies a **minimal** file — SDK import, `project()`, `pico_sdk_init()`, one
executable, `pico_add_extra_outputs` — and carries **no stdio routing at all**. Deciding
where the console lives is lesson 00's actual teaching, and it stays two lines the learner
adds themselves to a file they own from that moment on. The boilerplate is handed over; the
decision is not.

## Durable decisions

### pin-assignment

PS/2 clock on GP2 and PS/2 data on GP3 — adjacent and in that order, because a PIO program
addresses pins from a base index and `wait`/`in` on two adjacent pins is materially simpler
than on two scattered ones. Debug UART0 on GP0 and GP1 to the second Pico. GP4 reserved for
the offered safety catch, GP5 for the lesson 16 timing marker. GP23, GP24, GP25 and GP29
are used by the Pico board itself and are not available.

What breaks if a lesson contradicts it: lesson 07 and 08's PIO programs assume adjacency,
and lesson 16's capture correlation assumes a marker pin exists. Resolved.

### voltage-domains

The Model M runs at 5 V and is powered from VBUS. RP2040 GPIO is 3.3 V and is **not** 5 V
tolerant. A BSS138-type bidirectional MOSFET level shifter sits between the two, chosen
because the PS/2 clock and data lines are open-drain and either end may pull them low — a
resistor divider cannot work on such a line, and a unidirectional buffer breaks the
host-to-device transmit that lesson 09 needs. Pull-ups exist on both sides: the keyboard
supplies its own on the 5 V side, and the shifter module carries the 3.3 V side.

What breaks if a lesson contradicts it: lesson 09's transmit, and the hardware. Resolved.

### wire-format

The keyboard stays in **scan code set 2** and the adapter never asks it to switch. The
frame is eleven bits — start, eight data bits LSB first, odd parity, stop. For
device-to-host traffic the data line is valid on the falling clock edge; for host-to-device
traffic the device clocks the host's bits and samples them on the rising edge.

What breaks if a lesson contradicts it: any lesson assuming break equals make with bit 7
set, which is set 1 behaviour and produces a decoder that silently mangles half the
keyboard. Resolved.

### rx-interface

One receive interface — initialise, and a non-blocking pop of one byte — with two backends
selected at build time: the lesson 04–06 interrupt receiver and the lesson 08 PIO receiver.
Both must satisfy the same checks. The interrupt backend is kept for the life of the
course, as the reference implementation and as the thing lesson 08 and the offered latency
lesson measure against.

What breaks if a lesson contradicts it: the offload comparison loses its baseline, and a
lesson that reaches into a backend's internals makes the two non-interchangeable. Resolved.

### events-vs-state

The adapter holds a key-state bitmap as its single source of truth. PS/2 produces *events*
that mutate it; USB HID reports are *snapshots* built from it and sent only when it changes.
Nothing downstream of the decoder consumes PS/2 events directly.

What breaks if a lesson contradicts it: a report sent per PS/2 event gives stuck keys the
moment two events arrive within one polling interval, and the bug is intermittent and
miserable to find. This is the conceptual hinge of the whole course. Resolved.

### hid-contract

One HID interface, boot-protocol compatible: interface subclass 1, protocol 1, **no report
ID**, an 8-byte input report (modifier bitmap, reserved byte, six-key array) and a one-byte
LED output report. Six-key rollover with `ErrorRollOver` on overflow. The reason is
requirement 5 and 6 of the brief — no driver, and it works in a BIOS, where only boot
protocol is understood.

What breaks if a lesson contradicts it: adding a second top-level collection to *this*
interface forces report IDs, makes the input report nine bytes, and breaks boot protocol
silently — the device still works on a running desktop and fails in firmware setup. Any
debug or vendor channel therefore goes on a **separate interface**, which is what the
offered `a-second-interface-for-debugging` lesson does. Resolved.

The development VID/PID is the pid.codes test pair `1209:0001`, which is explicitly
allocated for exactly this and explicitly not for distribution. Lesson 11 says why a made-up
VID is not an option for anything shipped. Resolved.

### failure-posture

The adapter must start with no keyboard attached and pick one up when it appears; resync
after a parity or framing error rather than latching; release all held keys on error,
unplug or USB reset, so a key is never left down; and support USB remote wakeup, because an
ordinary keyboard wakes its host.

What breaks if a lesson contradicts it: a lesson that assumes the keyboard is present at
boot produces firmware that wedges on a cold start, which is exactly how the finished
object will be used. Resolved.

### debug-channel

The debug console is UART0 to a second Pico running `debugprobe`, deliberately **not** USB,
because USB is the artefact under test — the moment the firmware claims USB for HID, a USB
console is either gone or is itself a variable in the experiment. The same second Pico
provides SWD for lesson 16. The check scripts read this console.

What breaks if a lesson contradicts it: moving stdio to USB costs the learner their
diagnostic channel precisely during lessons 11 to 15, when enumeration is failing, and
makes every console-reading validator unrunnable. Resolved.

### Deliberately unresolved

- **Whether the finished perfboard build keeps the level-shifter module or uses discrete
  BSS138s and resistors.** Lesson 18 presents both and the learner chooses; the layout
  supplied covers the module, which is the lower-risk soldering job.
- **Whether the finished adapter carries the vendor debug interface.** The offered lesson
  adds it; the main path does not, and the acceptance test in lesson 18 must pass either
  way.
- **Which host the learner develops against.** The course recommends a machine the learner
  does not mind being typed into, and offers a firmware safety catch, but requires neither.

## Host tooling constraints (verified 2026-09-29)

Recorded here because these facts shaped the arc and a future author must not "correct"
them back. Verified on macOS 26.6.2 (Apple Silicon, SIP enabled) and from primary vendor
documentation.

- **Reading a device's descriptors back from the host works on all three OSes.**
  `hidapitester --get-report-descriptor` is the common tool; `ioreg -c IOHIDDevice -r -l`
  exposes `ReportDescriptor` as raw bytes on macOS with no root, and
  `/sys/class/hidraw/hidrawN/device/report_descriptor` does the same on Linux. On Windows
  the descriptor is *reconstructed* from preparsed data rather than read from the device,
  and USBTreeView's own documentation says report-descriptor requests usually fail. Lesson
  12 must not promise Windows learners byte-for-byte fidelity.
- **`system_profiler SPUSBDataType` is dead on macOS 26** — it returns an empty array and
  is absent from `-listDataTypes`. Only `SPUSBHostDataType` exists. Lesson text must not
  use the old name.
- **`SPUSBHostDataType` does not use `SPUSBDataType`'s key names either**, which is the
  half of that change that bites second. It emits `USBDeviceKeyVendorID`,
  `USBDeviceKeyProductID`, `USBDeviceKeyVendorName`, `USBDeviceKeySerialNumber` and
  `USBDeviceKeyLinkSpeed` — not `vendor_id`, `product_id`, `manufacturer` and
  `serial_num`. Code ported by changing only the data-type name parses the new output
  happily and finds zero devices, with no error anywhere. Found on this machine while
  testing `checks/_usb.py`, which now accepts both spellings.
- **`ioreg` lists the same HID collection once per client**, so a single-interface device
  looks composite unless the reader deduplicates. `checks/_usb.py` does.
- **Packet-level USB capture does not work on macOS.** No `XHC*` interface exists,
  `ifconfig XHC20 up` fails, and although `AppleUSBHostPacketFilter.kext` is present and
  loaded it never instantiates while SIP is enabled. The only documented route is
  `csrutil disable` from Recovery, which this course will not ask for. Hence
  `watch-the-enumeration` is offered rather than main-path, and its recommended route is a
  third Pico as a passive full-speed sniffer producing a pcap — cheap, OS-independent, and
  on-theme. usbmon on Linux and USBPcap on Windows remain the native routes; the USBPcap
  lesson text must carry its risk note, since its last release is from 2020 and there is an
  open BSOD report against Windows 11 25H2.
- **A host cannot read the input reports of a keyboard top-level collection.** Windows'
  Raw Input Manager opens keyboard collections exclusively at any privilege level; macOS
  gates them behind Input Monitoring *and* a non-exclusive open; Chrome's WebHID strips
  their reports, prunes the collection, and drops the device from `requestDevice()`
  entirely. This is why the course validates through the debug UART and not through the
  host, and why the vendor-usage-page workaround is a real lesson rather than a footnote.
- **Base the TinyUSB work on the `hid_boot_interface` example, not `hid_composite`.**
  `hid_composite` carries a report ID and therefore a nine-byte report; the learner would
  count nine bytes where lesson 12 says eight.

## Coverage

Topics this course owes the learner, named as a learner would ask about them:

microcontroller execution model · boot ROM and UF2 · XIP flash and the memory map ·
GPIO · push-pull vs open-drain · pull-up sizing · RC on a bus · logic levels and 3.3 V vs
5 V · level shifting · current budget · reading a pinout · interrupts · ISR latency · what
you may not do in an ISR · ISR and main-loop shared state · `volatile` · critical sections ·
lock-free single-producer ring buffers · framing state machines · resynchronisation and
timeouts · parity · RP2040 PIO · the PIO instruction set · PIO shift registers and autopush ·
clock dividers · protocol offload and how to measure it · PS/2 electrical interface ·
PS/2 framing both directions · bus arbitration on a shared line · scan code set 2 · make
and break · extended and break prefixes · typematic repeat · USB bus topology and addresses ·
endpoints and transfer types · USB enumeration · USB descriptors · HID report descriptors ·
usages, arrays and bitmaps · boot protocol vs report protocol · HID keyboard reports ·
modifiers · rollover · HID output reports and lock LEDs · USB suspend, resume and remote
wakeup · firmware architecture with swappable backends · where state lives in a small
firmware · SWD and gdb · reading a hard fault · the observer effect of `printf` on timing ·
logic analyser use · sample rate and triggering · soldering · continuity testing · strain
relief

Deliberately **not** covered, so a stuck learner knows they have hit a boundary and not a
hole:

USB host mode, hubs, USB 3, and isochronous or bulk transfers · DMA, which the RP2040 has
and this project does not need · an RTOS; the architecture is a superloop plus interrupts ·
Rust, MicroPython and CircuitPython · PCB design and fabrication · wireless of any kind ·
the Model M's internal matrix and controller beyond what rollover forces · reading your own
keyboard's HID input reports from the host, which no desktop OS permits · USB packet capture
on macOS, which does not work · NKRO beyond the offered lesson · ESP32-S3 and other
platforms, discussed once in lesson 00 and then left alone

## Proposed manifest fields

```yaml
bundle_format: 1
id: pico-ps2-usb-adapter
title: Build a PS/2 to USB HID Keyboard Adapter on the Raspberry Pi Pico
description: >
  Build an adapter that presents an IBM Model M over PS/2 to any modern computer
  as an ordinary USB HID keyboard, and learn the embedded, electrical, timing and
  protocol layers it stands on.
teaching_method: >
  Every stage ends in something you can observe on an instrument or on the host
  before the next one starts. You see the PS/2 signal before you decode it, you
  write the receiver with interrupts before you offload it to PIO, and you write
  every USB descriptor by hand. The tutor reads evidence off your board's debug
  console and never advances on an assertion.
subjects: [embedded, microcontrollers, rp2040, usb, hid, ps2, electronics, firmware, c]
aliases: [model m, keyboard adapter, ps2 to usb, raspberry pi pico, rp2040, pio,
          usb hid, tinyusb, mechanical keyboard, buckling spring, pico-sdk]
level: intermediate
style: [project-driven, interactive, long-form]
```

`assumes`: C including pointers and bit manipulation, the command line, git, and reading
reference documentation — all at a level that needs no teaching here. Explicitly **not**
assumed: any electronics, any firmware experience, any USB knowledge below the connector.

`covers` will be generated from the coverage list above.

## Depth decision

**Every lesson is authored now**, main path and offered track alike. Twenty main-path
lessons plus seven offered ones. No chapter is left as a map.

The cost of the alternative was the deciding factor: an unwritten chapter is drafted fresh
by each learner's tutor, differently every time, and the chapters that would have been left
unwritten here — USB descriptors, HID report descriptors, the events-to-state hinge — are
precisely the ones where a differently-drafted lesson would diverge most.

Estimated at 1.5 to 3 hours per lesson, so 30 to 50 hours for the main path. Recorded so a
later author knows the length was chosen and not accidental. If it must be shortened, the
intended lever is demoting `when-it-goes-wrong` and `robustness-and-the-real-world` to the
offered track, which costs the learner a device they have not hardened.

## Bill of materials

Recorded here because lead time is the one thing a learner cannot compress, and because
two of these choices are load-bearing on the design.

| Item | Note |
|---|---|
| An IBM Model M, or any PS/2 keyboard | the thing being adapted. Listed because a bill of materials that omits the subject is one nobody can shop from |
| Two USB data cables | one per Pico. A charge-only cable is the classic afternoon lost to a board that will not enumerate |
| Raspberry Pi Pico (RP2040) | the adapter itself. RP2350 works unchanged; RP2040 is chosen for the weight of community material a stuck learner will search |
| A **second** Pico, flashed as `debugprobe` | the debug console for every lesson and SWD for lesson 16. Not optional in practice — the validators read this console. Raspberry Pi's own Debug Probe accessory substitutes for it entirely; a 3.3 V USB-UART adapter substitutes for the console but not for SWD |
| BSS138-type 4-channel bidirectional level shifter | **load-bearing.** Not a resistor divider and not a unidirectional buffer; see `#voltage-domains` |
| PS/2 extension cable to cut open, or a mini-DIN-6 panel socket | the cable is easier to work with and gives strain relief for free |
| Breadboard and jumper wires | |
| Pin headers, unless both Picos are the pre-soldered Pico-H | needed before anything reaches a breadboard |
| Assorted resistors, 1 k to 10 k | for the pull-up experiment in lesson 02 |
| Multimeter | assumed present |
| Logic analyser, 8 channel, sigrok/PulseView compatible | assumed present. A cheap clone is sufficient at PS/2 speeds |
| Perfboard or stripboard, solder, small enclosure, heat-shrink | lesson 18 |
| Soldering iron, wire strippers, side cutters | lesson 18. Assumed by the word "solder" above and therefore worth listing outright |
| Oscilloscope | **not** assumed. Used only by the offered `see-the-edges-on-a-scope` lesson |
| A third Pico | **not** assumed. Only for the offered `watch-the-enumeration` lesson on a macOS host, as a passive USB sniffer |

A note the course states plainly rather than enforces: buggy firmware on an input device
types into whatever window has focus. Developing against a machine you do not mind being
typed into is recommended, and the offered `a-safety-catch` lesson adds a firmware gate for
learners who would rather solve it that way. Neither is required.

## Open questions

None outstanding for the author. The three items under *Deliberately unresolved* are
choices the learner makes during the course, not gaps in the design.

## Revision note — 2026-09-29, after the course-quality audit

The bundle was built from this spec, audited the same day, and then both were revised
together. The audit report is in `skomp/belay-authoring` at
`docs/audits/2026-09-29-pico-ps2-usb-adapter.md`; its findings are
`skomp/belay-bundles#28`. The author ruled on the three that were genuinely open.

**What changed in this spec, and why.**

1. **`CMakeLists.txt` is now supplied.** It was in *Not supplied, and deliberately so*, on
   the argument that a file edited in nearly every lesson must be the learner's. The audit
   scored the from-scratch write as the course's only toil site, because a single-platform
   course can ship exactly one such file. Both arguments survive: the bundle ships a minimal
   file with **no stdio routing at all**, and deciding where the console lives stays lesson
   00's teaching. See *Supplied files*.

2. **Lesson 18 became lessons 18 and 19.** At 473 lines it was the longest in the course and
   its own Purpose named the seam — construction, then acceptance. 18 now ends with the
   enclosure fitted and closes on `firmware-alive`; 19 is the acceptance suite and closes on
   `finished-adapter`. The main path is twenty lessons. No content was dropped.

3. **Three objectives were stated and never exercised**, at −3 each under the rubric: lesson
   00's XIP and memory-map objective, lesson 04's interrupt-entry objective, and lesson 11's
   transfer-types objective. Lesson 00's exercise was promoted from an optional deeper path
   to the main path; 04 and 11 gained completion conditions.

4. **The watchdog is now verified on the finished object.** Lesson 17 built it and nothing
   tested it again; lesson 19's acceptance list now wedges the soldered adapter and requires
   it to recover with the case shut.

5. **Two concepts were taught and never used** — `side-set` in lesson 07 and flash
   persistence in `remap-and-macros`. Both are trimmed to a pointer plus an optional deeper
   path, rather than left as attention the course never cashes in.

**What did not change.** The interrupt-receiver-before-PIO ordering, the debug-UART
validation channel, and `watch-the-enumeration` staying off the main path are the three
decisions this spec called load-bearing, and the audit found nothing against any of them.
No `required_for` gate exists, no `DESIGN.md` anchor goes unserved, and a learner who
declines every offer can still finish the course.
