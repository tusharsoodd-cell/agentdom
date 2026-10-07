# agentdom benchmark

Estimated tokens = characters / 4. Answerability = tasks whose target
is present and (for action tasks) clickable via a stable ref.

| page | format | tokens | nodes | extract ms | answerability |
| --- | --- | ---: | ---: | ---: | ---: |
| Wikipedia article | raw html | 58,869 | 1,898 | 2.0 | 1/4 |
| Wikipedia article | tree | 24,582 | 1,473 | 107.0 | 4/4 |
| Wikipedia article | tree (interactive) | 17,242 | 905 | 107.0 | 4/4 |
| Wikipedia article | json | 35,359 | 1,473 | 107.0 | 4/4 |
| Hacker News front page | raw html | 8,664 | 814 | 0.5 | 0/4 |
| Hacker News front page | tree | 7,874 | 733 | 33.1 | 4/4 |
| Hacker News front page | tree (interactive) | 5,886 | 487 | 33.1 | 4/4 |
| Hacker News front page | json | 13,735 | 733 | 33.1 | 4/4 |
| Wikipedia portal | raw html | 22,961 | 1,068 | 0.7 | 1/3 |
| Wikipedia portal | tree | 8,894 | 845 | 43.4 | 3/3 |
| Wikipedia portal | tree (interactive) | 8,065 | 752 | 43.4 | 3/3 |
| Wikipedia portal | json | 18,778 | 845 | 43.4 | 3/3 |

## Size reduction (raw HTML -> representation)

| page | -> tree | -> tree (interactive) | -> json |
| --- | ---: | ---: | ---: |
| Wikipedia article | 2.4x | 3.4x | 1.7x |
| Hacker News front page | 1.1x | 1.5x | 0.6x |
| Wikipedia portal | 2.6x | 2.8x | 1.2x |
