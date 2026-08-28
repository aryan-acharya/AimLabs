"""
game/difficulty.py - Difficulty scaling based on score or time
"""


class DifficultyManager:
    """
    Levels 15.
    Level increases every N hits.
    """
    def __init__(self, hits_per_level: int = 10):
        self.hits_per_level = hits_per_level
        self.current_level  = 1
        self.max_level      = 5

    def update_from_hits(self, total_hits: int):
        """Recalculate level based on total hits."""
        new_level = min(
            self.max_level,
            1 + total_hits // self.hits_per_level
        )
        changed = new_level != self.current_level
        self.current_level = new_level
        return changed   # True if level just changed

    def get_level(self):
        return self.current_level

    def get_display_name(self):
        names = ['', 'Easy', 'Normal', 'Hard', 'Expert', 'God Mode']
        return names[self.current_level]
