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
  });
};

function rellenar_destinos(){
  json_to_select('/inventario/orden_de_salida_producto/' + $('#id_origen_producto').val() + '/destinos_json/', '#id_destino_producto');
  $('#id_destino_producto').chosen({
    width: '100%',
    allow_single_deselect: true,
    no_results_text: 'Sin coincidencias',
    search_contains: true
  }).trigger("chosen:updated");
};
