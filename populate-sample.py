from common import *
from datastore import *

ndb.delete_multi(Round.query().fetch(keys_only=True))
ndb.delete_multi(Puzzle.query().fetch(keys_only=True))

# comment this out to keep the stats
ndb.delete_multi(Stats.query().fetch(keys_only=True))

# ROUND 1
querycache.delete('round1')

Round(parent = g.parent,
	id = 'round1',
	order = 1,
	name = 'ROUND 1',
).save()

Puzzle(parent = g.parent,
	id = 'puzzle-1',
	round = 'round1',
	order = 1,
	meta = False,
	name = 'Puzzle 1',
	answers = { 'one': {
					'final': True,
					'message': f'Good job solving this puzzle!',
				},
			},
).save()

# intermediate solutions (aka milestones) are noted with final = False
# tokens can be any dictionary containing whatever you want to be shown when
# someone solves a puzzle. it's up to the templates to display them
Puzzle(parent = g.parent,
	id = 'meta-1',
	round = 'round1',
	order = 2,
	meta = True,
	unlockPuzzleCount = 1,
	name = 'Meta 1',
	answers = { 'meta': {
					'final': True,
					'message': f'Good job solving this meta!',
					'tokens': { 'image': 'icon.png',
								'value': 'Token',
					},
				},
				'one': {
					'final': False,
					'message': f'Close, but no cigar.',
				}
			},
).save()

# ROUND 2
querycache.delete('final-round')

Round(parent = g.parent,
	id = 'final-round',
	order = 2,
	name = 'FINAL ROUND',
	unlockPuzzles = ['meta-1'],
).save()

Puzzle(parent = g.parent,
	id = 'meta-meta',
	round = 'final-round',
	order = 1,
	meta = True,
	metameta = True,
	name = 'Final Meta',
	answers = { 'five': {
					'final': True,
					'message': f'Good job finishing this hunt!',
					'tokens': { },
				},
				'moon': {
					'final': False,
					'message': f'How many?',
				}
			},
).save()
