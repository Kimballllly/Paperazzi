<?php
// Database credentials
$host = "paperazzi.cre40o0wmfru.ap-southeast-2.rds.amazonaws.com";
$user = "admin";
$password = "paperazzi";
$database = "paperazzi";

// Connect to the database
$conn = new mysqli($host, $user, $password, $database);

// Check connection
if ($conn->connect_error) {
    die(json_encode(["error" => "Connection failed: " . $conn->connect_error]));
}

// Fetch total jobs today
$result = $conn->query("SELECT COUNT(*) AS total_jobs_today FROM print_job_details WHERE DATE(created_at) = CURDATE()");
$total_jobs_today = $result->fetch_assoc()["total_jobs_today"];

// Fetch revenue today
$result = $conn->query("SELECT SUM(total_price) AS revenue_today FROM print_job_details WHERE DATE(created_at) = CURDATE()");
$revenue_today = $result->fetch_assoc()["revenue_today"] ?: 0;

// Fetch print jobs
$result = $conn->query("SELECT job_id, file_name, pages_to_print, color_mode, total_price, status, created_at FROM print_job_details ORDER BY created_at DESC LIMIT 10");
$print_jobs = [];
while ($row = $result->fetch_assoc()) {
    $print_jobs[] = $row;
}

// Return data as JSON
echo json_encode([
    "total_jobs_today" => $total_jobs_today,
    "revenue_today" => $revenue_today,
    "print_jobs" => $print_jobs
]);

$conn->close();
?>
