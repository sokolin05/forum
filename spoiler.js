<script src="https://ajax.googleapis.com/ajax/libs/jquery/1.12.4/jquery.min.js"></script>

$(function() {
        $(".wandererSpoilerHead").click(function() {
            $(this).toggleClass("wandererSpoiler");
            let a = $(this).next(".wandererSpoilerBody");
            a.toggleClass("active");
        });
    });
    let menu_hide = 0;
    function transition(name) {
      $('body,html').animate({scrollTop:$("#"+name).offset().top - $('nav').innerHeight() - 10}, 200);
 }
