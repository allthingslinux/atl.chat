<?php

/*
  PHP script to handle file uploads and downloads for Prosody's mod_http_upload_external

  Tested with Apache 2.2+ and PHP 5.3+

  ** Why this script?

  This script only allows uploads that have been authorized by mod_http_upload_external. It
  attempts to make the upload/download as safe as possible, considering that there are *many*
  security concerns involved with allowing arbitrary file upload/download on a web server.

  With that said, I do not consider myself a PHP developer, and at the time of writing, this
  code has had no external review. Use it at your own risk. I make no claims that this code
  is secure.

  ** How to use?

  Drop this file somewhere it will be served by your web server. Edit the config options below.

  In Prosody set:

    http_upload_external_base_url = "https://your.example.com/path/to/share.php/"
    http_upload_external_secret = "this is your secret string"

  ** License

  (C) 2016 Matthew Wild <mwild1@gmail.com>

  Permission is hereby granted, free of charge, to any person obtaining a copy of this software
  and associated documentation files (the "Software"), to deal in the Software without restriction,
  including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense,
  and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so,
  subject to the following conditions:

  The above copyright notice and this permission notice shall be included in all copies or substantial
  portions of the Software.

  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING
  BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
  NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
  DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

*/

/*\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\*/
/*         CONFIGURATION OPTIONS                   */
/*\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\*/

/* Change this to a directory that is writable by your web server, but is outside your web root */
$CONFIG_STORE_DIR = '/tmp';

/* This must be the same as 'http_upload_external_secret' that you set in Prosody's config file */
$CONFIG_SECRET = 'this is your secret string';

/* For people who need options to tweak that they don't understand... here you are */
$CONFIG_CHUNK_SIZE = 4096;

/*\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\*/
/*         END OF CONFIGURATION                    */
/*\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\*/

/* Do not edit below this line unless you know what you are doing (spoiler: nobody does) */

$upload_file_name = substr($_SERVER['PHP_SELF'], strlen($_SERVER['SCRIPT_NAME'])+1);
$store_file_name = $CONFIG_STORE_DIR . '/store-' . hash('sha256', $upload_file_name);

$request_method = $_SERVER['REQUEST_METHOD'];

/* Set CORS headers */
header('Access-Control-Allow-Methods: GET, PUT, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');
header('Access-Control-Max-Age: 7200');
header('Access-Control-Allow-Origin: *');

if(array_key_exists('v', $_GET) === TRUE && $request_method === 'PUT') {
	$upload_file_size = $_SERVER['CONTENT_LENGTH'];
	$upload_token = $_GET['v'];

	$calculated_token = hash_hmac('sha256', "$upload_file_name $upload_file_size", $CONFIG_SECRET);
	if(function_exists('hash_equals')) {
		if(hash_equals($calculated_token, $upload_token) !== TRUE) {
			error_log("Token mismatch: calculated $calculated_token got $upload_token");
			header('HTTP/1.0 403 Forbidden');
			exit;
		}
	}
	else {
		if($upload_token !== $calculated_token) {
			error_log("Token mismatch: calculated $calculated_token got $upload_token");
			header('HTTP/1.0 403 Forbidden');
			exit;
		}
	}
	/* Open a file for writing */
	$store_file = fopen($store_file_name, 'x');

	if($store_file === FALSE) {
		header('HTTP/1.0 409 Conflict');
		exit;
	}

	/* PUT data comes in on the stdin stream */
	$incoming_data = fopen('php://input', 'r');

	/* Read the data a chunk at a time and write to the file */
	while ($data = fread($incoming_data, $CONFIG_CHUNK_SIZE)) {
  		fwrite($store_file, $data);
	}

	/* Close the streams */
	fclose($incoming_data);
	fclose($store_file);

	// https://xmpp.org/extensions/xep-0363.html#upload
	// A HTTP status Code of 201 means that the server is now ready to serve the file via the provided GET URL.
	header('HTTP/1.0 201 Created');
	exit;
} else if($request_method === 'GET' || $request_method === 'HEAD') {
	// Send file (using X-Sendfile would be nice here...)
	if(file_exists($store_file_name)) {
		header('Content-Disposition: attachment');
		header('Content-Type: application/octet-stream');
		header('Content-Length: '.filesize($store_file_name));
		header("Content-Security-Policy: \"default-src 'none'\"");
		header("X-Content-Security-Policy: \"default-src 'none'\"");
		header("X-WebKit-CSP: \"default-src 'none'\"");
		if($request_method !== 'HEAD') {
			readfile($store_file_name);
		}
	} else {
		header('HTTP/1.0 404 Not Found');
	}
} else if($request_method === 'OPTIONS') {
} else {
	header('HTTP/1.0 400 Bad Request');
}

exit;
