$(document).ready(function() {

    var colours = [
		'#f44336', '#e91e63', '#9c27b0', '#673ab7', '#3f51b5', '#2196f3', '#03a9f4', '#00bcd4', '#009688', '#4caf50', '#8bc34a', '#cddc39', '#ffeb3b', '#ffc107', '#ff9800', '#ff5722', '#795548', '#ef9a9a', '#f48fb1', '#ce93d8', '#b39ddb', '#9fa8da', '#90caf9', '#81d4fa', '#80deea', '#80cbc4', '#a5d6a7', '#c5e1a5', '#e6ee9c', '#fff59d', '#ffecb3', '#ffcc80', '#ffab91', '#bcaaa4', '#c62828', '#ad1457', '#6a1b9a', '#4527a0', '#283593', '#1565c0', '#0277bd', '#00838f', '#00695c', '#2e7d32', '#558b2f', '#9e9d24', '#f9a825', '#ff8f00', '#ef6c00', '#d84315', '#4e342e'];

    var positions = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('');

    var platePadding = 10;
    var wellPadding = 8;

    var availableWidth = $('#plate-container').width();
    var plateWidth = ((availableWidth / 3) * 2);
    var plateHeight = (plateWidth / 3) * 2;

    var plateSize = plate_data.plates.plates[0].layout[0];

    var wellDiameter = ((plateWidth) / plateSize) - (wellPadding);

    // Plate is 1 -> 2/3

    var container = d3.select('#plate-container');

    var key = container.append('div').attr('class', 'key ui mini vertical menu');

    var hover = container.append('div')
        .attr('class', 'hover')
        .style('opacity', 0);

    var getTopPosition = function(d) {
        var row = positions.indexOf(d.coord[0]) + 1;
        if (row == 1) {
            return wellPadding + 'px'; //((row * wellDiameter)) + 'px';
        } else {
            return ((wellPadding * row) + (wellDiameter * (row - 1))) + 'px';
        }
    };

    var getLeftPosition = function(d) {
        var col = d.coord[1];
        if (col == 1) {
            return wellPadding + 'px';
        } else {
            return (((col - 1) * wellDiameter) + (wellPadding * col)) + 'px';
        }
    };

    var getContentsColour = function(d) {
        var substance = d[1];
        var substanceIdx = plate_data.plates.substances.indexOf(substance);
        var colourId = substanceIdx;
        if (substanceIdx >= colours.length) {
            colourId = substanceIdx % colours.length;
        }
        return colours[colourId];
    };

    var makeHoverHTML = function(d) {
        var output = '';
        $.each(d.contents, function(i, item) {
            var colour = getContentsColour(item);
            var colourBlob = '<span class="indicator" style="background: ' + colour + '"></span>';
            var showAmount = item[0];
            if (item[0] == 0) {
                var showAmount = '&infin;';
            }
            var amount = '&nbsp;<span class="amount">' + showAmount + ' nl</span>';
            output += '<span class="substance">'+ colourBlob + item[1] + amount + '</span>';
        });
        if (d.contents.length > 1) {
            output += '<div class="ui horizontal divider">Total</div>';
            output += '<span class="amount">' + d.total + ' nl</span>';
        }
        return output;
    };

    key.selectAll('div')
        .data(plate_data.plates.substances)
        .enter().append('div')
        .attr('class', 'item')
		.style('color', function(d, i) {
            var colourId = i;
            if (i >= colours.length) {
                colourId = i % colours.length;
            }
            return colours[colourId];
        })
		.text(function(d) { return d });

    var plates = container.selectAll('div.plate')
        .data(plate_data.plates.plates)
        .enter().append('div')
        .attr('class', 'plate')
        .style('width', (plateWidth + platePadding) + 'px')
        .style('height', (plateHeight + platePadding) + 'px')

    plates.append('div')
        .attr('class', 'title')
        .html(function(d) {
            var detail = ' <span class="detail">Position: ' + d.location + '</span>';
            return '<span class="ui label">' + d.label + detail + '</span>';
        })

    var wells = plates.selectAll('div.well')
        .data(function(d) { return d.wells; })
        .enter().append('div')
        .attr('class', 'well')
        .style('width', wellDiameter + 'px')
        .style('height', wellDiameter + 'px')
        .style('top', function(d) { return getTopPosition(d); })
        .style('left', function(d) { return getLeftPosition(d); })
        .on('mouseover', function(d) {
            if (d.contents.length > 0) {
                hover.transition()
                    .duration(200)
                    .style('opacity', 1);
                hover.html(makeHoverHTML(d))
                    .style('top', (d3.event.pageY) + 'px')
                    .style('left', (d3.event.pageX) + 'px')
            }
        })
        .on('mouseout', function(d) {
            hover.transition()
                .duration(200)
                .style('opacity', 0)
        })
        .html(function(d) {
            if (d.contents.length > 1) {
                return '<span class="contents number">' + d.contents.length + '</span>'
            } else if (d.contents.length == 1) {
                var colour = getContentsColour(d.contents[0]);
                return '<span class="contents" style="background: ' + colour + '"></span>'
            }
        });
});
