document.querySelectorAll('.utc-time').forEach(td => {
    const dt = new Date(td.dataset.utc);
    console.log(td.dataset);
    console.log(dt);
    td.textContent = dt.toLocaleString("sv-SE", {
        timeZone: "Asia/Taipei",
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit"
    });
});