$(document).ready(function () {
    /*
     * Easy Pie Charts - Used in widgets
     */
    function easyPieChart(id, trackColor, scaleColor, barColor, lineWidth, lineCap, size) {
        $('.'+id).easyPieChart({
            trackColor: trackColor,
            scaleColor: scaleColor,
            barColor: barColor,
            lineWidth: lineWidth,
            lineCap: lineCap,
            size: size
        });
    }
    
    /* Main Pie Chart */
    if ($('.main-pie')[0]) {
        easyPieChart('main-pie', 'rgba(255,255,255,0.2)', 'rgba(255,255,255,0.5)', 'rgba(255,255,255,0.7)', 7, 'butt', 148);
    }
    
    /* Others */
    if ($('.sub-pie')[0]) {
        easyPieChart('sub-pie', '#eee', '#ccc', '#2196F3', 4, 'butt', 95);
    }
    //if ($('.sub-pie-1')[0]) {
        //easyPieChart('sub-pie-1', '#eee', '#ccc', '#2196F3', 4, 'butt', 95);
    //}
    
    //if ($('.sub-pie-2')[0]) {
        //easyPieChart('sub-pie-2', '#eee', '#ccc', '#FFC107', 4, 'butt', 95);
    //}
    
    //if ($('.sub-pie-3')[0]) {
        //easyPieChart('sub-pie-3', '#eee', '#ccc', '#33DDAA', 4, 'butt', 95);
    //}
    
    //if ($('.sub-pie-4')[0]) {
        //easyPieChart('sub-pie-4', '#eee', '#ccc', '#DDAACC', 4, 'butt', 95);
    //}
});



