$(document).ready(function() {
    let elem = document.getElementById('actionTypesModalList');
    let options = {
        handle: '.handle',
        animation: 150,
        dataIdAttr: 'data-id'
    }
    let sortable = new Sortable(elem, options);
    $('#form-sort-order').on('submit', function() {
        document.getElementById('encoded_order').value = sortable.toArray().join();
    });
});
