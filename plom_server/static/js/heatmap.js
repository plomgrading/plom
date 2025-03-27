/*
    SPDX-License-Identifier: AGPL-3.0-or-later
    Copyright (C) 2023 Divy Patel
    Copyright (C) 2023 Colin B. Macdonald
*/

function renderHeatMap(data, divId) {
    // Clear existing contents of the div
    d3.select("#" + divId).html("");

    if (!data || !data.values|| data.values.length <= 1 || data.values[0].length <= 1) {
        d3.select("#" + divId)
            .append("div")
            .attr("class", "error")
            .text("No data for heatmap");
        return;
    }

    // Set up dimensions and margins
    const cellSize = 50; // Set the desired cell size
    const margin = { top: 40, right: 50, bottom: 20, left: 60 };
    const width = data.cols * cellSize + margin.left + margin.right;
    const height = data.rows * cellSize + margin.top + margin.bottom;

    // Create the SVG container
    const svg = d3.select("#" + divId)
        .append("svg")
        .attr("width", width)
        .attr("height", height);

    // Define the diagonal stripe pattern for the cells on the diagonal
    svg.append("pattern")
        .attr("id", "diagonal-stripe")
        .attr("patternUnits", "userSpaceOnUse")
        .attr("width", 4)
        .attr("height", 4)
        .append("path")
        .attr("d", "M-1,1 l2,-2 M0,4 l4,-4 M3,5 l2,-2")
        .attr("stroke", "#000")
        .attr("stroke-width", 1);

    // title for the heatmap
    svg.append("text")
        .attr("x", width / 2)
        .attr("y", margin.top * 0.67)
        .attr("text-anchor", "middle")
        .style("font-size", "20px")
        .text(data.title);

    // Create a color scale
    const colorScale = d3.scaleSequential(d3.interpolateBlues)
        .domain([-1, 1]);

    // Create the heat map cells
    const cells = svg.selectAll("rect")
        .data(data.values.flat())
        .enter()
        .append("rect")
        .attr("x", (d, i) => (i % data.cols) * cellSize + margin.left) // Set the x-coordinate based on the column index
        .attr("y", (d, i) => Math.floor(i / data.cols) * cellSize + margin.top) // Set the y-coordinate based on the row index
        .attr("width", cellSize) // Set the desired cell width
        .attr("height", cellSize) // Set the desired cell height
        .attr("fill", (d, i) => {
            return d == 1 ? "url(#diagonal-stripe)" : colorScale(d);
        }) // Apply diagonal stripes to the cells on the diagonal
        .on("click", cellClicked); // Add click event listener

    // Add x-axis labels at the bottom
    const xLabels = svg.selectAll(".xLabel")
        .data(data.xLabel)
        .enter()
        .append("text")
        .text(d => d)
        .attr("class", "xLabel")
        .attr("x", (d, i) => (i + 0.5) * cellSize + margin.left)
        .attr("y", height - 2)
        .style("text-anchor", "middle");

    // Add y-axis labels
    const yLabels = svg.selectAll(".yLabel")
        .data(data.yLabel)
        .enter()
        .append("text")
        .text(d => d)
        .attr("class", "yLabel")
        .attr("x", margin.left * 0.9)
        .attr("y", (d, i) => (i + 0.6) * cellSize + margin.top)
        .style("text-anchor", "end");

    // Add x-axis title
    svg.append("text")
        .attr("class", "xTitle")
        .attr("x", width / 2)
        .attr("y", margin.top / 2)
        .style("text-anchor", "middle")
        .text(data.xTitle);

    // Add y-axis title
    svg.append("text")
        .attr("class", "yTitle")
        .attr("transform", "rotate(-90)")
        .attr("x", -(margin.top + height) / 2)
        .attr("y", margin.left / 3)
        .style("text-anchor", "middle")
        .text(data.yTitle);

    // Add color bar gradient
    const defs = svg.append("defs");
    const gradientId = "colorGradient";
    const gradient = defs.append("linearGradient")
        .attr("id", gradientId)
        .attr("x1", "0%")
        .attr("y1", "100%")
        .attr("x2", "0%")
        .attr("y2", "0%");

    gradient.selectAll("stop")
        .data(colorScale.ticks().map((tick, i, nodes) => ({
            offset: `${100 * i / (nodes.length - 1)}%`,
            color: colorScale(tick)
        })))
        .enter()
        .append("stop")
        .attr("offset", d => d.offset)
        .attr("stop-color", d => d.color);

    // Add color bar
    const colorBarWidth = 10;
    const colorBarHeight = height - margin.top - margin.bottom;
    const colorBar = svg.append("g")
        .attr("class", "colorBar")
        .attr("transform", `translate(${width - margin.right + 10}, ${margin.top})`);

    colorBar.append("rect")
        .attr("x", 0)
        .attr("y", 0)
        .attr("width", colorBarWidth)
        .attr("height", colorBarHeight)
        .attr("fill", `url(#${gradientId})`);

    const colorBarScale = d3.scaleLinear()
        .domain([-1, 1])
        .range([colorBarHeight, 0]);

    const colorBarAxis = d3.axisRight(colorBarScale)
        .ticks(5);

    // Append the axis to the colorBar group
    const colorBarAxisGroup = colorBar.append("g")
        .attr("class", "colorBarAxis")
        .call(colorBarAxis)
        .selectAll(".tick line")
        .attr("stroke", "#888") // Add style for tick lines
        .attr("stroke-dasharray", "2,2"); // Add style for dashed tick lines
}

function cellClicked(d) {
    const cellInfoDiv = d3.select("#cell_popup");
    cellInfoDiv.text(d.target.__data__);
}
