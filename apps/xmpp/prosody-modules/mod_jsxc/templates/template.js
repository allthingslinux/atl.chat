$(function() {
	let jsxc = new JSXC({
		loadConnectionOptions: function(username, password) {
			return Promise.resolve(%s);
		}
	});

	let formElement = $('#jsxc_login_form');
	let usernameElement = $('#jsxc_username');
	let passwordElement = $('#jsxc_password');

	jsxc.watchForm(formElement, usernameElement, passwordElement);
});
