"""Werkstatt-Rollen (OP-140 + OP-141).

Rollenmodule: builder/, builder_apply.py, complete_run.py, planner_split.py,
read_only_task.py, verify_task.py und verify_recovery.py. Rollen werden
bedarfsgesteuert am Checkpoint dispatcht; Phasenmodule dienen als
Executor-/Kompatibilitaetsgrenze und duerfen keine globale Reihenfolge erzwingen.
"""
