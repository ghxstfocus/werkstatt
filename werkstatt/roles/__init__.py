"""Werkstatt-Rollen (OP-140 + OP-141).

Rollenmodule: builder/, planner_split.py und verify_recovery.py. Rollen
werden bedarfsgesteuert am Checkpoint dispatcht; Phasenmodule dienen als
Executor-/Kompatibilitaetsgrenze und duerfen keine globale Reihenfolge
erzwingen.
"""
