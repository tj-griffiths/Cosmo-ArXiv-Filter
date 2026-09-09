# Text-cleaning helpers used for the Cosmo pipeline

import re

_GREEK_LETTERS = [
    "alpha", "beta", "gamma", "delta", "epsilon", "zeta", "eta", "theta",
    "iota", "kappa", "lambda", "mu", "nu", "xi", "omicron", "pi", "rho",
    "sigma", "tau", "upsilon", "phi", "chi", "psi", "omega",
]

def clean_latex(text: str) -> str:
    text = re.sub(r"\\(?:mathrm|mathcal|mathbf|text|rm)\{([^{}]*)\}", r"\1", text)

    for letter in _GREEK_LETTERS:
        text = re.sub(rf"\\{letter}(?![a-zA-Z])", letter, text, flags=re.IGNORECASE)
        text = re.sub(rf"\\{letter.capitalize()}(?![a-zA-Z])", letter.capitalize(), text)

    replacements = {
        r"\\times": "x",
        r"\\pm": "+/-",
        r"\\sim": "~",
        r"\\approx": "~",
        r"\\lesssim": "<~",
        r"\\gtrsim": ">~",
        r"\\odot": "solar",
        r"\\ll": "<<",
        r"\\gg": ">>",
        r"\\rm": "",
        r"\\[,;:!]": " ",  # thin/med/thick spacing commands -> a plain space
    }
    for pattern, repl in replacements.items():
        text = re.sub(pattern, repl, text)

    text = re.sub(r"\^\{([^{}]*)\}", r"^\1", text)  # superscripts
    text = re.sub(r"_\{([^{}]*)\}", r"_\1", text)  # subscripts

    text = text.replace("$", "")  # remove $ math delimiters
    text = re.sub(r"\\[a-zA-Z]+\{([^{}]*)\}", r"\1", text)  # \cmd{X} -> X
    text = re.sub(r"\\[a-zA-Z]+", "", text)  # \cmd -> ""

    text = " ".join(text.split())  # collapse whitespace
    return text