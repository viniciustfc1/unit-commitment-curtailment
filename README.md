# Unit Commitment with Curtailment

This repository contains codes developed within the course **Planejamento Energético**, part of the **Programa de Pós-Graduação em Engenharia Elétrica (PPEE)** at the **Universidade Federal de Juiz de Fora (UFJF)**.

The project focuses on the implementation of a **thermal Unit Commitment model**, progressively incorporating **operational constraints** and **curtailment factors**, with applications in power system planning and operation studies.

---

## 📌 Project Description

The codes in this repository address:
- Formulation of a **thermal Unit Commitment** problem
- Inclusion of **technical and operational constraints**
- Modeling of **curtailment** as a limiting factor on generation
- A modular code structure, aiming at clarity, reusability, and future expansion

The repository is under continuous development, following the progression of the course.

---

## 📂 Repository Structure

The current structure of the repository is organized as follows:

```
├── main.py
├── functions/
│   └── main_functions.py
├── requirements.txt
└── README.md
```

### `main.py`
Main project file, responsible for:
- Defining the overall execution flow
- Loading data and parameters
- Calling auxiliary functions
- Running the Unit Commitment model

### `functions/`
Directory containing auxiliary function scripts used by the main code.

- `main_functions.py`:  
  Currently contains all auxiliary functions required for building and running the model.

This structure is intended to keep the code organized and facilitate future extensions.

---

## ⚙️ Installation

### Clone the repository

```bash
git clone https://github.com/viniciustfc1/unit-commitment-curtailment.git
cd unit-commitment-curtailment
```

---

## 📦 Requirements

The project dependencies are listed in the `requirements.txt` file.

Install them using:

```bash
pip install -r requirements.txt
```

It is recommended to use a virtual environment (e.g., `venv` or `conda`).

---

## 🎓 Academic Context

This repository is intended for **academic purposes**, supporting the development and understanding of computational models in the Planejamento Energético course of the PPEE/UFJF program.

