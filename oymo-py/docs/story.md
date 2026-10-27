# Oymomo and Her Stars

In Uzbek folk tales, **Oymomo** is the Mother Moon, and the stars are her children.

**Oymo** (the first four letters of *Oymomo*) is the name of the project, its CLI (`oymo`), and its file extension (`.oymo`). Every source file starts with `language <name>`.

- **Oymomo** (`language oymomo`) is the mother language. She sits closest to the machine and binds other languages and C to native code. Every language in Oymo lowers into her.
- **Stars** are the languages born from Oymomo:
  - **Alcor** (`language alcor`) and **Mizar** (`language mizar`) are the binary star pair — the "Horse and Rider" in the handle of the Big Dipper:
    - **Alcor** is the Rider: a small systems language with only what the compiler needs to build itself.
    - **Mizar** is the Horse: the general-purpose language that extends Alcor.

```
Mizar  (general-purpose language, extends Alcor)
  └─► Alcor  (kernel systems language, builds the compiler)
        └─► Oymomo  (mother language, binds languages and C to the machine)
```

Finding a name for a new language is hard — I spent hours on it. If you ever get stuck naming yours, feel free to pick a star from any constellation, and it will be one of Oymomo's stars too.