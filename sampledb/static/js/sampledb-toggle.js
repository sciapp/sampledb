function sdbtoggle(id) {
    $( '#'+id ).toggle();
    if ($( '#'+id ).is(":hidden")) {
        $( '#'+id ).html().replaceAll("hide", "show");
    }
    else {
        $( '#'+id ).html().replaceAll("show", "hide");
    }
}