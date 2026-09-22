# ✏️ Lineart Converter

![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey.svg)

> *“A tool born from the desire to create, learn, and share without barriers.”*

**Lineart Converter** is an open-source desktop application that transforms any colored image or illustration into a clean line art drawing or stencil, **running 100% locally on your machine**. 

Built with privacy and accessibility in mind for artists, illustrators, and designers: no subscriptions, no watermarks, and zero data uploaded to external servers.

---

## 🖤 A Message to the Community (Why I Need Your Help)

> *This project was built in the quiet hours of my room—through long nights of trial, error, and lines of code written with the sole dream of offering the creative community a free, privacy-respecting alternative.*
>
> *Rebuilding these image processing algorithms from scratch was a massive challenge for me. I poured all my current knowledge, time, and heart into this codebase. **Yet, with genuine humility, I recognize my limitations.** I know this code is far from perfect, that the Tkinter interface could take a massive leap forward, and that the core algorithms can be optimized in ways my current skill level doesn't yet allow me to see.*
>
> *To you, experienced developer reading this: **please don't let this effort stop halfway.** Your knowledge could be the bridge that grants thousands of creators access to a truly professional, free, and private tool.*
>
> *If you ever felt that spark to build something meaningful when you were starting out, I ask you today to lend a hand to this project. Every Pull Request, every OpenCV performance tweak, and every UI enhancement isn't just code—**it’s helping me keep a community-driven tool alive**.*

---

## 🎨 Processing Modes

The core motor faithfully replicates 5 distinct image processing modes:

* 🖌️ **Edges:** Clean sketch/line art output (ideal for digital drawings and artwork).
* ✍️ **Thin:** Ultra-thin edge detection based on Canny precision.
* ⚖️ **Threshold:** Pure high-contrast black & white powered by histogram equalization.
* 🌗 **Adaptive:** Localized adaptive algorithm, ideal for preserving details in dark or heavily shaded areas.
* 🎯 **Color:** Isolates and converts to black only the areas matching a selected target color.

Each mode features real-time dynamic sliders for **Sharp ↔ Soft** (detail/blur depth) and **Black ↔ White** (threshold sensitivity).

---

## 🛠️ How You Can Contribute (Open Roadmap)

If you feel inspired to push this project to the next level, here are key areas where your experience would make an enormous difference:

- [ ] **Performance & Multithreading:** Implement asynchronous image rendering to prevent UI freezes on high-res images.
- [ ] **UI Modernization:** Migrate from standard Tkinter to modern frameworks like `CustomTkinter`, `PyQt`, or `PySide`.
- [ ] **Mathematical Optimization:** Fine-tune the color distance ($\Delta E$) calculation algorithm inside `rapidresizer_core.py`.
---

## 🚀 Requirements & Quickstart

### Prerequisites
* Python 3.9 or higher
* OpenCV, NumPy, Pillow

```bash
# Clone the repository
git clone [https://github.com/YOUR-USERNAME/lineart-converter.git](https://github.com/YOUR-USERNAME/lineart-converter.git)
cd lineart-converter

# Install dependencies
pip install -r requirements.txt

# Run the application
python lineart_gui.py
