# Lacrosse Expected Goals (xG)

A lacrosse version of the expected goals stat, built from a published shot-location heat map. Each spot on the field gets a value based on how often shots from that area become goals.

![Lacrosse goal conversion rates by shot location](image_RIf6ZQ.png)

*Goal conversion rates by shot location. Source: Myers et al. (2021), The Sport Journal.*

## What is xG?

Expected goals (xG) measures the quality of a scoring chance. Instead of treating every shot the same, it estimates how likely each shot is to become a goal. The stat is best known from soccer and hockey.

For example, a shot with an xG of 0.40 has a 40% estimated chance of scoring. Add up a team's shot values, and you get the number of goals its chances would typically produce.

## How It Works

1. **Map the field:** Divide the heat map into a grid, using yards as the coordinate system.
2. **Assign values:** Give each grid cell an xG value based on its conversion rate in the heat map.
3. **Score each shot:** Find the cell where the shot was taken and use that cell's value.
4. **Add up the totals:** Sum the shot values to get xG for a player, team, or game.

### Example

These values are for illustration only:

| Shot | Location | xG |
|------|----------|------|
| 1 | Close to the goal | 0.40 |
| 2 | Mid-range | 0.15 |
| 3 | Long-range | 0.05 |
| **Total** | | **0.60** |

These three shots would be expected to produce 0.60 goals.

## Why xG Matters in Lacrosse

Shot totals don't show whether a team is creating good chances. In the source study, xG was more closely tied to winning than raw shot counts:

| Measure | xG | Shots |
|---------|----|-------|
| Correlation with team win percentage | 0.65 | 0.13 |
| Win rate when beating the opponent in this stat | 73% | 65% |

The study covered 4,497 NCAA Division I shots from 55 games in the 2019 season. Its sample was limited, with 20 of the games involving the same team, and the correlations were based on only 14 teams.

## Limitations

- **Location only:** This project values a shot by where it was taken. It doesn't account for factors such as defensive pressure, goalie position, or shot type.
- **Different method from the paper:** The authors built their xG model with logistic regression using shot distance, shot angle, and whether the shot came off a pass. This project uses the published heat map instead, so its values won't exactly match the paper's model.
- **Limited sample:** The conversion rates come from one season of Division I games and may not carry over to other levels of play.

## Credits and Data Sources

- **Heat map:** The shot-chart graphic (`image_RIf6ZQ.png`) comes from the paper below.
- **Paper:** Myers, B. R., Burns, M., Coughlin, B. Q., & Bolte, E. (2021). [On the Development and Application of an Expected Goals Model for Lacrosse](https://thesportjournal.org/article/on-the-development-and-application-of-an-expected-goals-model-for-lacrosse/). *The Sport Journal*.
