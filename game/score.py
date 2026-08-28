"""
game/score.py - Score, accuracy, and countdown timer tracking
"""


class ScoreTracker:
    def __init__(self, game_duration: float = 60.0):
        self.game_duration = game_duration
        self.reset()

    def reset(self):
        self.hits         = 0
        self.shots_fired  = 0
        self.time_left    = self.game_duration
        self.game_over    = False
        self.best_streak  = 0
        self._streak      = 0
        self.game_started = False   # timer frozen until first shot

    def record_shot(self):
        self.shots_fired  += 1
        self.game_started  = True   # start the clock on first shot

    def record_hit(self):
        self.hits    += 1
        self._streak += 1
        self.best_streak = max(self.best_streak, self._streak)

    def record_miss(self):
        self._streak = 0

    def record_penalty(self):
        """Obstacle hit: subtract 1 point and break the streak."""
        self.hits    -= 1
        self._streak  = 0

    @property
    def accuracy(self):
        if self.shots_fired == 0:
            return 0.0
        return (self.hits / self.shots_fired) * 100.0

    @property
    def streak(self):
        return self._streak

    def update(self, dt: float):
        if not self.game_over and self.game_started:
            self.time_left = max(0.0, self.time_left - dt)
            if self.time_left <= 0.0:
                self.game_over = True

    def get_summary(self):
        return {
            'hits'      : self.hits,
            'shots'     : self.shots_fired,
            'accuracy'  : self.accuracy,
            'best_streak': self.best_streak,
        }
