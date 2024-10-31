//Jscript para validaciones

function json_to_select(url, select_selector) {
	$.getJSON(url, function(data) {
		var opt=$(select_selector);
		var old_val=opt.val();
		opt.html('');
		$.each(data, function () {
			opt.append($('<option/>').val(this.id).text(this.value));
		});
		opt.val(old_val);
		opt.change();
	})
};

//Funcion para validar el metodo segun el tipo de ensayo
$(function(){
	$('#id_solicitud').change(function(){
		json_to_select('/laboratorio/lote_solicitud/?solicitud=' + $('#id_solicitud').val(), '#id_lote_muestra');
	})
});

<!-- Cambios de valores y activaciones/desactivaciones de campos dependientes -->

$(document).ready(function () {
	$('#id_solicitud').change();
});

//Funcion para validar el metodo segun el tipo de ensayo
$(function(){
	$('#id_tipo_ensayo').change(function(){
		json_to_select('/laboratorio/tipo_ensayo_metodo/?tipo_ensayo=' + $('#id_tipo_ensayo').val(), '#id_metodo_ensayo');
	})
});

<!-- Cambios de valores y activaciones/desactivaciones de campos dependientes -->

$(document).ready(function () {
	$('#id_tipo_ensayo').change();
});
