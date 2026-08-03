from pywikihow import HowTo

how_to = HowTo("https://www.wikihow.com/Tie-a-Tie")

for step in how_to.steps:
    if step.picture:
        print(step.number, step.summary, "->", step.picture)
