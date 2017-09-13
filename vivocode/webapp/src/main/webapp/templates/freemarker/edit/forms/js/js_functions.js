/* $This file is distributed under the terms of the license in /doc/license.txt$ */

/*Used for methods such as inherit*/
//In this case, superclass_proto is a variable, not a function
function inherit(superclass_proto, newclass_extensions) {
	/*function F() {}
	F.prototype = superclass_proto;
	return new F();
	*/
	//Utilizing jquery extend instead
	//We can use it directly as well but just testing which of these will work
	//var inherited = $.extend({}, superclass_proto, newclass_extensions);
	//Changes the object directly
	//For whatever reason, only extending the object directly seems to work
	//as far as recognizing the variable
	//ALTHOUGH the global variable has already been defined?
	var inherited = $.extend(superclass_proto, newclass_extensions);

	return inherited;
}