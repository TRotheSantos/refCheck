const shrinking_header = document.querySelector(".shrinking-header");
if (shrinking_header) {
    const header_expand = getComputedStyle(document.documentElement).getPropertyValue('--shrinking-header-expand-scale');
    const init_header_height = header_expand * shrinking_header.offsetHeight;
    shrinking_header.style.height = init_header_height + "px";

    window.onscroll = function () {
        scrollFunction()
    };

    function scrollFunction() {
        var new_height = Math.max((init_header_height - window.scrollY), 0);
        shrinking_header.style.height = new_height + "px";
        if (new_height < init_header_height / header_expand) {
            document.querySelector("#text-logo").classList.add("scroll-out");
        } else {
            document.querySelector("#text-logo").classList.remove("scroll-out");
        }
    }
}

const sticky_header = document.querySelector(".sticky-header");
if (sticky_header) {
    document.querySelector(".content").style.marginTop = (sticky_header.offsetHeight - parseInt(getComputedStyle(sticky_header).paddingTop, 10)) + "px";
}
