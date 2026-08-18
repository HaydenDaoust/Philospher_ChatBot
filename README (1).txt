SOURCE TEXT — Nicomachean Ethics
==================================

The loader now fetches the text automatically from the MIT Internet Classics
Archive at runtime — no manual download required.

    python backend/loader.py

This downloads the W. D. Ross translation from:
    http://classics.mit.edu/Aristotle/nicomachaen.mb.txt

and extracts only the following chapters before embedding:

    Book I   — chapters 1, 2, 7, 10        (topic: eudaimonia)
    Book II  — chapters 1, 2, 6, 9         (topic: doctrine_of_mean)
    Book III — chapters 6–12               (topic: doctrine_of_mean)
    Book VI  — chapters 5, 7, 12, 13       (topic: phronesis)
    Book X   — chapter 9                   (topic: habit_and_practice)

NOTES
-----
- The W. D. Ross translation is in the public domain.
- Re-run loader.py only when you change the chapter selection or chunking
  parameters; the ChromaDB at chroma_db/ is reused otherwise.
- An internet connection is required when running loader.py.
