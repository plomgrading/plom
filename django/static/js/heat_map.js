/*
    SPDX-License-Identifier: AGPL-3.0-or-later
    Copyright (C) 2023 Divy Patel
*/

function renderHeatMap(data, divId) {
    // Clear existing contents of the div
    d3.select("#" + divId).html("");

    // Set up dimensions and margins
    const cellSize = 40; // Set the desired cell size
    const margin = { top: 20, right: 20, bottom: 40, left: 20 }; // Higher margin on bottom for labels
    const width = data.cols * cellSize + margin.left + margin.right;
    const height = data.rows * cellSize + margin.top + margin.bottom;

    // Create the SVG container
    const svg = d3.select("#" + divId)
        .append("svg")
        .attr("width", width)
        .attr("height", height);

    // Create a color scale
    const colorScale = d3.scaleSequential(d3.interpolateGreens)
        .domain([d3.min(data.values.flat()), d3.max(data.values.flat())]);

    // Create the heat map cells
    const cells = svg.selectAll("rect")
        .data(data.values.flat())
        .enter()
        .append("rect")
        .attr("x", (d, i) => (i % data.cols) * cellSize + margin.left) // Set the x-coordinate based on the column index
        .attr("y", (d, i) => Math.floor(i / data.cols) * cellSize + margin.top) // Set the y-coordinate based on the row index
        .attr("width", cellSize) // Set the desired cell width
        .attr("height", cellSize) // Set the desired cell height
        .attr("fill", d => colorScale(d)); // Set the cell color based on the value

    // Add x-axis labels
    const xLabels = svg.selectAll(".xLabel")
        .data(data.xLabel)
        .enter()
        .append("text")
        .text(d => d)
        .attr("class", "xLabel")
        .attr("x", (d, i) => (i + 0.5) * cellSize + margin.left)
        .attr("y", height - margin.bottom / 2)
        .style("text-anchor", "middle");

    // Add y-axis labels
    const yLabels = svg.selectAll(".yLabel")
        .data(data.yLabel)
        .enter()
        .append("text")
        .text(d => d)
        .attr("class", "yLabel")
        .attr("x", margin.left / 2)
        .attr("y", (d, i) => (i + 0.5) * cellSize + margin.top)
        .style("text-anchor", "middle");
}