/*
    SPDX-License-Identifier: AGPL-3.0-or-later
    Copyright (C) 2023 Divy Patel
    Copyright (C) 2023 Colin B. Macdonald
*/

function renderHist(data, divId) {
    // Clear existing contents of the div
    d3.select("#" + divId).html("");

    if (!data || !data.values || data.values.length <= 1 || data.values[0].length <= 1) {
        d3.select("#" + divId)
            .append("div")
            .attr("class", "error")
            .text("No data for histogram");
        return;
    }

    // Set up dimensions and margins
    const margin = { top: 50, right: 30, bottom: 50, left: 50 };
    const width = 400 - margin.left - margin.right;
    const height = 300 - margin.top - margin.bottom;

    // Create SVG element with margins
    const svg = d3.select("#" + divId)
        .append("svg")
        .attr("width", width + margin.left + margin.right)
        .attr("height", height + margin.top + margin.bottom)
        .append("g")
        .attr("transform", `translate(${margin.left},${margin.top})`);

    // title for the histogram
    svg.append("text")
        .attr("x", width / 2)
        .attr("y", -margin.top / 2)
        .attr("text-anchor", "middle")
        .style("font-size", "20px")
        .text(data.title);

    // Create x and y scales
    const xScale = d3.scaleBand()
        .domain(data.values.map(d => d.label))
        .range([0, width])
        .padding(0.1);

    const yScale = d3.scaleLinear()
        .domain([0, d3.max(data.values, d => d.value)])
        .range([height, 0]);

    // Create x and y axes
    const xAxis = d3.axisBottom(xScale);
    const yAxis = d3.axisLeft(yScale);

    // Append x and y axes to the SVG
    svg.append("g")
        .attr("class", "axis-x")
        .attr("transform", `translate(0,${height})`)
        .call(xAxis);

    svg.append("g")
        .attr("class", "axis-y")
        .call(yAxis);

    // Create bars
    svg.selectAll("rect")
        .data(data.values)
        .enter()
        .append("rect")
        .attr("x", d => xScale(d.label))
        .attr("y", d => yScale(d.value))
        .attr("width", xScale.bandwidth())
        .attr("height", d => height - yScale(d.value))
        .attr("fill", "steelblue");

    // Add x-axis label
    svg.append("text")
        .attr("class", "axis-label")
        .attr("x", width / 2)
        .attr("y", height + margin.bottom - 10)
        .style("text-anchor", "middle")
        .text(data.xLabel);

    // Add y-axis label
    svg.append("text")
        .attr("class", "axis-label")
        .attr("transform", "rotate(-90)")
        .attr("x", -height / 2)
        .attr("y", -margin.left)
        .attr("dy", "1em")
        .style("text-anchor", "middle")
        .text(data.yLabel);
}
