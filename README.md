# Discus-2cT Lift Calculator


---

## 👤 Author

Created by **Mikołaj Basiaga**  
If you use this project or have suggestions, feel free to contribute or open an issue.
I kept everything in a simple engineering form, so it’s easy to read and debug.

---

## Version 1 Features
- Comprehensive aerodynamic force modeling (CL/CD calculations)
- Interactive GUI built with PySide6 + Matplotlib/Seaborn
- Realistic stall behavior with smooth exponential decay
- Dynamic range limiting to avoid erratic post-stall behavior
- Multi-configuration support (15m/18m wings, flap settings, ballast)
- Weather API integration (`program/environment.py` + `program/weather.py`)  
- Real-time monitoring of air density, pressure and temperature 

---

## Version 2 Roadmap
- Weather API integration (utilizing `program/environment.py` and `program/weather.py`)
- Real-time atmospheric condition monitoring
- Enhanced performance calculations with live weather data

---

## What’s next (Version 2+ roadmap (Future))
- Asynchronous data handling (so weather updates don’t block the GUI)  
- Model improvements:  
- Incorporating Reynolds number effects (scale & speed sensitivity)  
- Using more accurate polar curve data (CL/CD vs. alpha) from literature or measurements  

---

## Technical Details 2d vs 3d


The model is a bit of both:
- It starts with **2D thin airfoil theory** (CL vs. alpha).
- Then applies **3D finite wing corrections** (aspect ratio and efficiency factor).
- Drag includes **induced drag** (so it behaves like a real wing).
- Stall is approximated with Viterna–Corrigan, which is empirical.

So it’s not just a flat airfoil polar, and not a full 3D CFD either. Let’s say a practical compromise: 2D theory + 3D corrections.

---

## Simplifications

- Reynolds number is not included (so no speed/scale effects).  
- Spanwise load is boiled down to a single efficiency factor `e`.  
- CL and CD are not from real polar curves, just approximated.  

--- 


### ℹ Flap and drag coefficients – background

The values related to flaps and drag (such as changes in CL/CD or stall angle shifts) are not taken from a single precise dataset.  
Instead, they were derived from a **blend of available reference data and manual tuning** to keep the model both realistic and easy to work with.

Key references:
- [Schempp-Hirth Discus-2 – official site](https://www.schempp-hirth.com/en/sailplanes/discus/discus-2ct)  
- [Wikipedia: Schempp-Hirth Discus-2](https://en.wikipedia.org/wiki/Schempp-Hirth_Discus-2)  
  (notes that the standard Discus achieves a maximum glide ratio of about **42.5:1**)

Because not all aerodynamic polars are publicly available, most of the coefficients here are **simplified or estimated**.  
They should be seen as practical approximations that produce reasonable performance across different spans, flap settings, and ballast configurations.

---

## Installation & Usage
```bash
pip install -r assets/requirements.txt
python program/main.py
```

---

## References

- Anderson, J. D. *Fundamentals of Aerodynamics*  
- McCormick, B. W. *Aerodynamics, Aeronautics and Flight Mechanics*  
- Viterna & Corrigan – *NASA Report on post-stall airfoil performance*  


## 📜 License

This project is released under the **MIT License** – free to use, modify and share, provided that the original copyright and license notice are included.