const video = document.getElementById('videoPlayer');

function skipBackward() {
    video.currentTime -= 5; // Skip backward by 5 seconds
}

function skipForward() {
    video.currentTime += 5; // Skip forward by 5 seconds
}
