"use strict";
const dateOptions = { year: 'numeric', month: 'short', weekday: 'long', day: 'numeric' };
const timeOptions = { hour: '2-digit', minute: '2-digit', hour12: false, timeZoneName: 'short' };
const shownAttempts = 5;

function hm(seconds) {
	seconds += 60;
	var h = Math.floor(seconds/3600);
	var m = Math.floor((seconds - 3600*h)/60);
	var msg = '';

	if (h > 0)
		msg += `${h} hour${(h > 1 ? 's' : '')}`;

	if (m > 0)
		msg += `${h > 0 ? ' and' : ''} ${m} minute${(m > 1 ? 's' : '')}`;

	return msg;
}

function localizeDates() {
	var dates = document.getElementsByClassName('date');

	for (var i = 0; i < dates.length; i++) {
		const utcDate = new Date(dates[i].innerHTML.replace(' ', 'T') + 'Z');
		dates[i].innerHTML = utcDate.toLocaleString('en-US', dateOptions) + ' at ' + utcDate.toLocaleString('en-US', timeOptions);
	}
}

function localizeTimestamps() {
	var dates = document.getElementsByClassName('date');

	for (var i = 0; i < dates.length; i++) {
		const utcDate = new Date(1000*dates[i].textContent);
		dates[i].innerHTML = utcDate.toLocaleString('en-US', dateOptions) + ' at ' + utcDate.toLocaleString('en-US', timeOptions);
	}
}

function showHints() {
	const hints = document.getElementById('hintlist');
	const button = document.getElementById('hints');

	hints.classList.toggle('show');
	button.classList.toggle('pressed');
	return false;
}

function showWriteup(solved) {
	const puzzle = document.getElementById('puzzle');
	const banner = document.getElementById('banner');
	const button = document.getElementById('solution');
	const puzzleAnswer = document.getElementById('puzzle-answer');

	puzzle.classList.toggle('reveal');
	banner.classList.toggle('reveal');
	button.classList.toggle('pressed');

	if (puzzleAnswer && !solved) {
		const userAnswer = document.getElementById('user-answer');
		userAnswer.classList.toggle('visible');
		puzzleAnswer.classList.toggle('visible');
	}

	return false;
}

function hintsTimer() {
	var delays = document.getElementsByClassName('delay');
	var now = parseInt(Date.now()/1000);

	for (var i = 0; i < delays.length; i++) {
		delays[i].endTime = now + parseInt(delays[i].innerHTML);
		delays[i].textContent = hm(delays[i].innerHTML);
	}

	let intervalId = setInterval(() => {
		var now = parseInt(Date.now()/1000);

		for (var i = 0; i < delays.length; i++) {
			if (delays[i].endTime > now) {
				delays[i].textContent = hm(delays[i].endTime - now);
			} else {
				clearInterval(intervalId);
				location.reload();
			}
		}
	}, 60000);
}

function checkAnswer() {
	const dialog = document.getElementById('dialog');
	const closeDialogButton = document.getElementById('closeDialog');
	const input = document.getElementById('attempt');

	function closeDialog(event) {
		if (event.target === dialog || event.target === closeDialogButton) {
			dialog.classList.add('hidden');
			closeDialogButton.removeEventListener('click', closeDialog);
			dialog.removeEventListener('click', closeDialog);
			input.removeEventListener('keydown', arrowKeys);
		}
	}

	dialog.classList.remove('hidden');
	input.focus();
	closeDialogButton.addEventListener('click', closeDialog);
	dialog.addEventListener('click', closeDialog);
	input.addEventListener('keydown', arrowKeys);

	return false;
}

function changeFormStatus(id, enabled) {
	const form = document.getElementById(id);
	const elements = form.elements;

	for (let i = 0; i < elements.length; i++) {
		elements[i].disabled = !enabled;
	}
}

function up(event) {
	event.preventDefault();
	let input = event.target;

	if (input.idx < input.attempts.length-1) {
		input.idx++;
		input.value = input.attempts[input.idx];
	}

	input.focus();
}

function down(event) {
	event.preventDefault();
	let input = event.target;

	if (input.idx > 0) {
		input.idx--;
		input.value = input.attempts[input.idx];
	}

	input.focus();
}

function arrowKeys(event) {
	switch (event.key) {
		case 'ArrowUp':
			up(event);
			break;
		case 'ArrowDown':
			down(event);
			break;
	}
}

function updateAttempts(milestones, attempts, guessesLeft, delay) {
	var limitedView = true;

	function showAttempts() {
		const ul = document.getElementById('attempts');
		const allAttempts = document.getElementById('all-attempts');
		const input = document.getElementById('attempt');

		allAttempts.removeEventListener('click', showAttempts);
		ul.innerHTML = '';
		input.attempts = [''];
		input.idx = 0;

		for (let guess of milestones) {
			let li = document.createElement('li');
			li.className = 'milestone';
			li.textContent = guess;
			ul.insertBefore(li, ul.firstChild);
		}

		if (attempts) {
			let entries = Object.entries(attempts);
			entries.sort((a, b) => b[1] - a[1]);

			for (let [guess, timestamp] of entries) {
				input.attempts.push(guess);

				if (!limitedView || input.attempts.length-1 <= shownAttempts) {
					let li = document.createElement('li');
					li.className = 'guess';
					li.textContent = guess;
					ul.appendChild(li);
				}
			}

			if (Object.keys(attempts).length > shownAttempts) {
				allAttempts.innerHTML = limitedView ? '🔻' : '🔺';
				limitedView = !limitedView;
				allAttempts.addEventListener('click', showAttempts);
			}

			input.focus();
		}
	}

	showAttempts();
	const warning = document.getElementById('warning');

	if (guessesLeft <= 0) {
		warning.innerHTML = `No guess left, please wait for <span id="delay">${hm(delay)}</span>.`;
		changeFormStatus('answer-form', false);

		let endTime = parseInt(Date.now()/1000) + delay;
		let delayElement = document.getElementById('delay');
		let intervalId = setInterval(() => {
			var now = parseInt(Date.now()/1000);

			if (endTime > now) {
				delayElement.textContent = hm(endTime - now);
			} else {
				clearInterval(intervalId);
				warning.innerHTML = '';
				changeFormStatus('answer-form', true);
			}
		}, 60000);
	} else if (guessesLeft < 2)
		warning.innerHTML = `${guessesLeft} guess left.`;
	else
		warning.innerHTML = `${guessesLeft} guesses left.`;
}

function submitAnswer(event, puzzleSlug) {
	event.preventDefault();

	const submit = document.getElementById('submit');
	const input = document.getElementById('attempt');
	const congrats = document.getElementById('congrats');
	const message = document.getElementById('message');
	const data = { puzzle: puzzleSlug, guess: input.value.replace(/[^a-zA-Z]/g, '') }

	submit.disabled = true;
	input.value = '';
	message.innerHTML = '';
	congrats.innerHTML = '';

	fetch('/guess', {
		method: 'POST',
		credentials: 'include',
		headers: {
			'Content-Type': 'application/json',
		},
		body: JSON.stringify(data),
	}).then(response => {
		submit.disabled = false;

		if (response.status === 401) {
			warning.innerHTML = 'You need to be logged in to submit an answer';
			return;
		}
		return response.json();
	}).then(response => {
		if (response) {
			if (response.error) {
				warning.innerHTML = response.error;
			} else if (response.correct) {
				const puzzleMessage = document.getElementById('puzzle-message');
				puzzleMessage.innerHTML = response.message;

				if (response.final || response.banner) {
					const solution = document.getElementById('solution');
					const puzzleAnswer = document.getElementById('user-answer');
					const puzzleMessages = document.getElementById('puzzle-messages');
					congrats.innerHTML = `<b>${response.guess}</b> is correct!`;

					message.innerHTML = `<p>${response.message}</p>`;
					puzzleAnswer.innerHTML = response.guess;
					congrats.style.display = 'block';
					puzzleAnswer.style.display = 'block';
					puzzleMessages.style.display = 'flex';

					if (solution && response.final) {
						solution.style.display = 'flex';
						solution.onclick = function() {
							location.hash = "#spoiler";
							location.reload();
						}
						
						const hints = document.getElementById('hints');
						if (hints) {
							hints.onclick = function() {
								location.reload();
							}
						}
					}
				} else {
					message.innerHTML = `<p>${response.message}</p>`;
				}

				if (response.final) {
					const answer = document.getElementById('answer');
					const warning = document.getElementById('warning');

					answer.style.display = 'none';
					warning.innerHTML = '';
					changeFormStatus('answer-form', false);
				} else {
					updateAttempts(response.milestones, response.attempts, response.guessesLeft, response.delay);
				}
			} else {
				updateAttempts(response.milestones, response.attempts, response.guessesLeft, response.delay);
			}
		}
	}).catch(error => {
		submit.disabled = false;
		console.error(error);
	});

	return false;
}

let copyToClipboard;

if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
	copyToClipboard = function () {
		const text = document.getElementById("copy-text").innerText;
		navigator.clipboard.writeText(text).then(() => {
			const message = document.getElementById("clipboard");
			message.style.display = "inline-block";
			setTimeout(() => {
				message.style.display = "none";
			}, 3000);
		}).catch (err => {
			console.log(err);
		});
	};
} else {
	copyToClipboard = () => {
		alert("Your browser doesn't support copying to clipboard.");
	};
}

function sortTeams(teams, teamName, teamId) {
	const teamList = Object.entries(teams);
	const withFinishTime = teamList.filter(([name, team]) => team.time !== "" && !team.testsolver);
	const withoutFinishTime = teamList.filter(([name, team]) => team.time === "" && !team.testsolver);
	const testSolvers = teamList.filter(([name, team]) => team.testsolver);
	const options = { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false, timeZoneName: 'short' };
	const tableBody = document.querySelector('#teams tbody');

	withFinishTime.sort(([nameA, teamA], [nameB, teamB]) => {
		return teamA.time.localeCompare(teamB.time);
	});

	withoutFinishTime.sort(([nameA, teamA], [nameB, teamB]) => {
		if (teamA.solves === teamB.solves) {
			if (teamA.lastsolve === teamB.lastsolve) {
				return nameA.localeCompare(nameB);
			} else {
				return teamA.lastsolve.localeCompare(teamB.lastsolve);
			}
		} else {
			return teamB.solves-teamA.solves;
		}
	});

	const sortedTeams = [...withFinishTime, ...withoutFinishTime, ...testSolvers];
	var rank = 0;

	sortedTeams.forEach(([name, team]) => {
		var row = document.createElement('tr');
		const rankCell = document.createElement('td');

		if (!team.testsolver)
			rank++;

		rankCell.textContent = team.time && !team.testsolver ? rank : '';
		row.appendChild(rankCell);

		const nameCell = document.createElement('td');
		nameCell.className = 'team-name';
		nameCell.innerHTML = name;
		row.appendChild(nameCell);

		if (team.solves != undefined) {
			const solveCell = document.createElement('td');
			solveCell.textContent = team.solves;
			row.appendChild(solveCell);
		}

		const timeCell = document.createElement('td');

		if (team.time) {
			const utcDate = new Date(team.time.replace(' ', 'T') + 'Z');
			const formattedDate = utcDate.toLocaleString('en-US', options);
			timeCell.textContent = formattedDate;
			row.className = 'finisher';

			if (name == teamName)
				nameCell.className += ' success winner';
			else
				nameCell.className += ' winner';
		} else {
			if (name == teamName)
				nameCell.className += ' me';

			timeCell.textContent = '';
		}

		row.appendChild(timeCell);
		tableBody.appendChild(row);
	});
}

