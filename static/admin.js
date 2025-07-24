"use strict";

document.addEventListener('DOMContentLoaded', () => {
		const showAddBtn = document.getElementById('show-add-btn');
		const showEditBtn = document.getElementById('show-edit-btn');
		const addContainer = document.getElementById('add-container');
		const editContainer = document.getElementById('edit-container');

		inputDates();
		localizeDates();

		if (showAddBtn) {
			showAddBtn.addEventListener('click', () => {
					addContainer.classList.toggle('hidden');

					if (addContainer.classList.contains('hidden')) {
							showAddBtn.textContent = '➕';
					} else {
							showAddBtn.textContent = '➖';
					}
			});
		}

		if (showEditBtn) {
			showEditBtn.addEventListener('click', () => {
					editContainer.classList.toggle('hidden');

					if (editContainer.classList.contains('hidden')) {
							showEditBtn.textContent = '✏️';
					} else {
							showEditBtn.textContent = '📝';
					}
			});
		}
});

function inputDates() {
	var dates = document.getElementsByClassName('datetime');
	var zones = document.getElementsByClassName('zone');
	var timezones = document.getElementsByClassName('timezone');
	var timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;

	if (timezones) {
		for (var i = 0; i < timezones.length; i++) {
			timezones[i].value = timezone;
		}
	}

	if (zones) {
		for (var i = 0; i < zones.length; i++) {
			zones[i].textContent = timezone;
		}
	}

	if (dates) {
		for (var i = 0; i < dates.length; i++) {
			const utcDate = new Date(dates[i].value.replace(/ /, 'T') + 'Z');
			const year = utcDate.getFullYear();
			const month = String(utcDate.getMonth() + 1).padStart(2, '0');
			const day = String(utcDate.getDate()).padStart(2, '0');
			const hours = String(utcDate.getHours()).padStart(2, '0');
			const minutes = String(utcDate.getMinutes()).padStart(2, '0');
			dates[i].value = `${year}-${month}-${day}T${hours}:${minutes}`;
		}
	}
}

function localizeDates() {
	var dates = document.getElementsByClassName('date');

	for (var i = 0; i < dates.length; i++) {
		var d = dates[i].innerHTML.replace(' ', 'T');

		if (d.indexOf('+') == -1)
			d += 'Z';

		const utcDate = new Date(d);
		dates[i].innerHTML = utcDate.toLocaleString('en-US', dateOptions);
	}
}

function addPuzzleSelection(count, field, puzzles, selection) {
	var puzzleOptions = '<option value="">None</option>';

	puzzles.sort((a, b) => {
		if (a.round < b.round) return -1;
		if (a.round > b.round) return 1;
			return a.order - b.order;
	});

	puzzles.forEach(puzzle => {
		var selected = (puzzle.slug == selection ? 'selected' : '');
		puzzleOptions += `<option value="${puzzle.slug}" ${selected}>${puzzle.round}: ${puzzle.name}</option>`;
	});

	var newField = document.createElement('div');
	newField.className = 'form-row';
	newField.innerHTML = `<label>Puzzle ${count}</label>
<select name="${field+count}">${puzzleOptions}</select>`;
	document.getElementById(field).appendChild(newField);
}

function addFieldAnswer(count, field, label, fieldValue, param) {
	var parentDiv = document.getElementById(field+'s');
	var fieldCount = field + count;
	var labelCount = label + ' ' + (count == 1 ? '' : count);

	var newField = document.createElement('div');
	newField.className = 'form-row';
	newField.innerHTML = `<label>${labelCount}</label><input type="text" name="${fieldCount}" value="${fieldValue}" required>`;
	parentDiv.appendChild(newField);

	var newFinal = document.createElement('div');
	newFinal.className = 'form-row';
	newFinal.innerHTML = `<label>${labelCount} is final?</label><input type="checkbox" name="final${count}" ${param.final == 1 ? 'checked' : ''}>`;
	parentDiv.appendChild(newFinal);

	var newMessage = document.createElement('div');
	newMessage.className = 'form-row';
	newMessage.innerHTML = `<label>${labelCount} Message</label><textarea type="text" name="message${count}" rows=5>${param.message || ''}</textarea>`;
	parentDiv.appendChild(newMessage);

	var newTokens = document.createElement('div');
	var tokenGrid = document.createElement('div');
	tokenGrid.className = 'form-grid';
	newTokens.innerHTML = 'Tokens (key, value)&nbsp;';
	const button = document.createElement('button');
	button.textContent = '+';
	button.type = 'button';
	newTokens.appendChild(button);
	newTokens.appendChild(tokenGrid);

	var tokenCount = 1;
	if (param.tokens) {
		for (var [key, value] of Object.entries(param.tokens)) {
			var newToken = document.createElement('div');
			newToken.className = 'form-row';
			newToken.innerHTML = `<label>${labelCount} Token ${tokenCount}</label><div><input type="text" name="token${count}Key${tokenCount}" value="${key}"><input type="text" name="token${count}Value${tokenCount}" value="${value}"></div>`;
			tokenGrid.appendChild(newToken);
			tokenCount++;
		}
	}

	function addToken() {
		var newToken = document.createElement('div');
		newToken.className = 'form-row';
		newToken.innerHTML = `<label>${labelCount} Token ${tokenCount}</label><div><input type="text" name="token${count}Key${tokenCount}" value=""><input type="text" name="token${count}Value${tokenCount}" value=""></div>`;
		tokenGrid.appendChild(newToken);
		tokenCount++;
	}

	button.addEventListener('click', addToken);

	parentDiv.appendChild(newTokens);
}

function addFieldTime(count, field, label, fieldValue, timeValue) {
	var parentDiv = document.getElementById(field+'s');
	var fieldCount = field + count;
	var fieldTimeCount = field + 'Time' + count;
	var labelCount = label + ' ' + count;

	var newField = document.createElement('div');
	newField.className = 'form-row';
	newField.innerHTML = `<label>${labelCount}</label><textarea type="text" name="${fieldCount}">${fieldValue}</textarea>`;
	parentDiv.appendChild(newField);

	var newTime = document.createElement('div');
	newTime.className = 'form-row';
	newTime.innerHTML = `<label>${labelCount} Time</label><div><input type="datetime-local" class="datetime" name="${fieldTimeCount}" value="${timeValue}" /><span class="zone"></span></div>`;
	parentDiv.appendChild(newTime);
	inputDates();
}

// teams page
function teamListener(teams) {
	const names = document.getElementsByClassName('team-name');
	const popup = document.getElementById('popup');

	for (var i = 0; i < names.length; i++) {
		const nameCell = names[i];
		const team = teams[nameCell.textContent];

		if (!team)
			continue;

		if (team.testsolver)
			nameCell.className += ' test';
		else if (!team.visible)
			nameCell.className += ' grey';

		nameCell.style.cursor = 'pointer';

		nameCell.addEventListener('click', (event) => {
			popup.innerHTML = showTeam(event.target.textContent);
			popup.style.display = 'block';
			popup.style.left = event.pageX + 'px';
			popup.style.top = `${event.pageY + 10}px`;

			const clickOut = (event) => {
				if (!nameCell.contains(event.target) && !popup.contains(event.target)) {

					popup.style.display = 'none';
					document.removeEventListener('click', clickOut);
				}
			}

			document.addEventListener('click', clickOut);
		});
	}
}

function showTeam(name) {
	const team = teams[name];
	var html;

	if (team.testsolver)
		html = `<h2 class="error">${name}</h2>`;
	else
		html = `<h2>${name}</h2>`;

	html += '<u>Unlocked Rounds</u>:<ul>';
	for (const [slug, time] of Object.entries(team.unlocked)) {
		const utcDate = new Date(1000*time);
		const date = utcDate.toLocaleString('en-US', dateOptions) + ' at ' + utcDate.toLocaleString('en-US', timeOptions);
		html += `<li>${slug}: ${date}</li>`;
	}
	html += '</ul>';

	html += '<u>Solved Puzzles</u>:<ul>';
	for (const slug of team.solved) {
		html += `<li>${slug}</li>`;
	}
	html += '</ul>';

	if (team.lastsolve && team.lastsolve != '9999') {
		const utcDate = new Date(team.lastsolve.replace(' ', 'T') + 'Z');
		html += `<u>Last Solve</u>:<ul><li>${utcDate.toLocaleString('en-US', dateOptions) + ' at ' + utcDate.toLocaleString('en-US', timeOptions)}</li></ul>`;
	}

	html += '<u>Puzzle Milestones</u>:<ul>';
	for (const [slug, answers] of Object.entries(team.milestones)) {
		html += `<li>${slug}:<ul>`;
		for (const [answer, value] of Object.entries(answers)) {
			html += `<li>${answer}</li>`;
		}
		html += '</ul></li>';
	}
	html += '</ul>';

	if (team.testsolver)
		html += `<a class="error" href="#" onclick="setTestSolver('${team.key}', 0)">Remove Testsolver Status</a>`;
	else
		html += `<a class="error" href="#" onclick="setTestSolver('${team.key}', 1)">Set as Testsolver</a>`;
	return html;
}

function setTestSolver(key, test) {
	fetch(`/adminteam?key=${key}&test=${test}`).then(response => response.text()).then(response => {
		alert(response);
		location.reload();
	}).catch(error => {
		alert('Failed to change the team ' + error.message);
		console.log(error);
	});
}

function dataHash(str) {
	let hash = 0;

	for (let i = 0; i < str.length; i++) {
		hash = (hash * 31 + str.charCodeAt(i)) | 0;
	}

	return hash >>> 0;
}
