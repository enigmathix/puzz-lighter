import { initializeApp } from "https://www.gstatic.com/firebasejs/10.12.3/firebase-app.js";
import { getDatabase, ref, onChildAdded, onChildChanged, query, orderByChild, startAt } from 'https://www.gstatic.com/firebasejs/10.12.3/firebase-database.js';
import { getAuth, signInWithCustomToken } from 'https://www.gstatic.com/firebasejs/10.12.3/firebase-auth.js';
import { getAnalytics } from "https://www.gstatic.com/firebasejs/10.12.3/firebase-analytics.js";

export function showNotification(puzzle) {
	if (puzzle && puzzle.name) {
		const sound = document.getElementById('applause');
		sound.play().catch(error => { });

		const notifications = document.getElementById('notifications');
		const notification = document.createElement('div');
		notification.className = 'notification';
		notification.innerHTML = `<a href="/puzzle/${puzzle.slug}">${puzzle.name}</a> is solved!`;
		notifications.appendChild(notification);

		setTimeout(() => {
			notification.remove();
		}, 10000);
    }
}

export function subscribe(path, callback, token) {
	const firebaseConfig = {
		// FIXME use values given in firebase datastore
		apiKey: "",
		authDomain: "",
		databaseURL: "",
		projectId: "",
		storageBucket: "",
		messagingSenderId: "",
		appId: "",
		measurementId: ""
	};

	if (!firebaseConfig.apiKey)
		return;

	// Initialize Firebase
	const app = initializeApp(firebaseConfig);
	const database = getDatabase(app);
	const dbRef = ref(database, path);
	const analytics = getAnalytics(app);

	if (token) {
		signInWithCustomToken(getAuth(), token).then(() => {
			onChildAdded(query(dbRef, orderByChild("timestamp"), startAt(Date.now()-3600000, 'timestamp')), (key) => callback(key.val()));
			onChildChanged(dbRef, (key) => callback(key.val()));
		});
	} else {
		onChildChanged(dbRef, (key) => callback(key.val()));
	}
}
