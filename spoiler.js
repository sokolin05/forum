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
