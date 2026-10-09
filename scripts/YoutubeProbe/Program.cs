using YoutubeExplode;
using YoutubeExplode.Videos.Streams;

using var timeout = new CancellationTokenSource(TimeSpan.FromMinutes(3));
using var youtube = new YoutubeClient();
Console.WriteLine(typeof(YoutubeClient).Assembly.FullName);
var manifest = await youtube.Videos.Streams.GetManifestAsync(args[0], timeout.Token);
var video = manifest.GetVideoOnlyStreams()
    .Where(s => s.VideoQuality.MaxHeight <= 720)
    .OrderByDescending(s => s.VideoQuality.MaxHeight).First();
var audio = manifest.GetAudioOnlyStreams().GetWithHighestBitrate();
Directory.CreateDirectory(args[1]);
await youtube.Videos.Streams.DownloadAsync(video, Path.Combine(args[1], "video." + video.Container.Name), cancellationToken: timeout.Token);
await youtube.Videos.Streams.DownloadAsync(audio, Path.Combine(args[1], "audio." + audio.Container.Name), cancellationToken: timeout.Token);
