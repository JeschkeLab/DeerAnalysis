# DeerAnalysis 2026

![GitHub Release](https://img.shields.io/github/v/release/JeschkeLab/DeerAnalysis?include_prereleases)
![GitHub Downloads (all assets, all releases)](https://img.shields.io/github/downloads/JeschkeLab/DeerAnalysis/total)
![GitHub License](https://img.shields.io/github/license/JeschkeLab/DeerAnalysis)


DeerAnalysis 2026 is major re-design and re-release of the popular dipolar-EPR data processing tool, DeerAnalysis. 
DeerAnalysis was originally released in 2004, as a matlab based GUI for Tikhnov-regularisation based approaches for extracting distance distributions from Double-Electron-Electron-Resonance (DEER) data, it has been updated multiple times since then most recently in 2022. In xxx DeerAnalysis gained support for neural-network based fitting in the form of DeerNet.

In the 2026 release, DeerAnalysis moved to a modern Python and Javascript based software stack, gaining support for multi-pathway fitting, compactness criterion for non-parametric models, and a completely redesigned user interface. Additionally, a new data/fit management software was implemented, allowing users to easily manage and compare multiple datasets and fits. Support for DeerNet was retained. The parametric and non-parametric fitting is powered by the latest version of [DeerLab](https://github.com/JeschkeLab/DeerLab), which is also available as a standalone package for Python. 


## Improvements over DeerAnalysis 2022

- Regularisation and parametric based fitting now using the latest DeerLab 1.2
- Dataset and fit managment, with high-quality comparison
- Based on a modern software stack (Python and Javascript)
- Compiled support on all major operating Systems
- Multi-pathway support (from DeerLab)
- Support for compactness criterion for non-parametric models (DeerLab)
- Support for global and population based fitting (DeerLab)

## Installation

DeerAnalysis 2026 is avaliable in pre-compiled binaries for Windows, Mac and Linux. The latest release can be found on the [GitHub releases page](https://github.com/JeschkeLab/DeerAnalysis/releases/latest). There is **no** need to install Python or any dependencies, simply download the latest release for your operating system and run the executable.


## Citing DeerAnalysis

When you use DeerAnalysis in your work, please cite the following publications:

 **DeerLab: a comprehensive software package for analyzing dipolar electron paramagnetic resonance spectroscopy data** <br>
 Luis Fábregas Ibáñez, Gunnar Jeschke, Stefan Stoll <br>
 Magn. Reson., 1, 209–224, 2020 <br>
 <a href="https://doi.org/10.5194/mr-1-209-2020"> doi.org/10.5194/mr-1-209-2020</a>

**Deep neural network processing of DEER data** <br>
 Steven G. Worswick, James A. Spencer, Gunnar Jeschke, Ilya Kuprov' <br>
 Science Advances 2018 <br>
 <a href="https://doi.org/10.1126/sciadv.aat5218"> doi.org/10.1126/sciadv.aat5218</a>

## License

DeerAnalysis is licensed under the [MIT License](LICENSE).

Copyright (c) 2026 by the Jeschke Lab, ETH Zurich. All rights reserved.
