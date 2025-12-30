/*
* Local timestamps
*/
(function () {
var timeTags = document.getElementsByTagName("time");
var i = 0, tag, date;
while(timeTags[i]) {
tag = timeTags[i++];
if(date = tag.getAttribute("datetime")) {
date = new Date(date);
tag.textContent = date.toLocaleTimeString(navigator.language);
tag.setAttribute("title", date.toString());
}
}
if(document.forms.length>0){
document.forms[0].elements.p.addEventListener("change", function() {
document.forms[0].submit();
});
}
})();

