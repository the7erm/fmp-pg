DEFAULT_RATING = cfg.get('Defaults', 'rating', 6, int)
DEFAULT_SCORE = cfg.get('Defaults', 'score', 5, int)
DEFAULT_PERCENT_PLAYED = cfg.get('Defaults', 'percent_played', 50.0, float)
DEFAULT_TRUE_SCORE = (((DEFAULT_RATING * 2 * 10.0) + (DEFAULT_SCORE * 10.0) + 
                        DEFAULT_PERCENT_PLAYED) / 3)

MAX_TRUE_SCORE = (((6 * 2 * 10.0) + (10 * 10.0) + 
                    100.0) / 3)
