# belay-bundles

Tutorial bundles for [Belay](https://github.com/skomp/belay).

Each subfolder is one self-contained bundle.

```
belay-bundles/
├── durable-event-broker/                 # one bundle
├── pico-ps2-usb-adapter/
├── portable-bytebeat-wav/
├── portable-fixed-window-rate-limiter/
├── rust-automaton-db/
└── webgl-typescript-scene/               # and another
    ├── tutorial.yaml
    ├── COURSE.md
    ├── DESIGN.md
    ├── STATE.template.md
    └── lessons/
```

## What a bundle is

A bundle is a **course**: written once, used by many learners. It carries no
learner progress.

A learner's progress lives in an **instance** — a `tutorial/` directory inside
that learner's own workspace, created by the runner when they start the course.
The instance is the only place a `STATE.md` ever exists.

The mechanical rule:

> A bundle contains `STATE.template.md` and never `STATE.md`.
> An instance contains `STATE.md` and never `STATE.template.md`.

## Adding a bundle

1. Create a subfolder named after the bundle `id`.
2. Follow the authoring contract: `skills/belay/references/bundle-format.md`
   in the Belay repository.
3. Validate it before committing.
4. Register it in a catalogue so a runner can find it.

## Bundles

| id | Title | Subjects | Level |
|---|---|---|---|
| `cpp-png-inspector` | C++ for C Programmers: Build a PNG Inspector | cpp, c, systems-programming, binary-formats, cmake | beginner-to-intermediate |
| `durable-event-broker` | Build a Durable Event Broker in Go | go, event-streaming, storage, distributed-systems | intermediate-to-advanced |
| `orange-pi-network-appliance` | Build a Linux Network Appliance on the Orange Pi Zero 3 | linux-networking, routing, nat, wifi, bluetooth, systemd, embedded-linux | intermediate |
| `pico-ps2-usb-adapter` | Build a PS/2 to USB HID Keyboard Adapter on the Raspberry Pi Pico | embedded, microcontrollers, rp2040, usb, hid, ps2, electronics, firmware, c | intermediate |
| `portable-bytebeat-wav` | Make Music with Integer Arithmetic | programming, audio, bytebeat, binary-formats | beginner-to-intermediate |
| `portable-fixed-window-rate-limiter` | Build a Fixed-Window Rate Limiter | programming, testing, api-design, rate-limiting | intermediate |
| `rust-automaton-db` | Learn Rust by Building AutomatonDB | rust, databases, distributed-systems | intermediate-to-advanced |
| `webgl-typescript-scene` | Learn WebGL 2 by Building a 3D Scene | webgl2, computer-graphics, typescript | intermediate |

## Licence

MIT. See `LICENSE`.

One licence covers the whole repository, and it covers a course entirely: the lesson
prose, the exercises, the design documents and the code fragments inside them. A bundle
carries no licence of its own and `tutorial.yaml` has no field for one.
