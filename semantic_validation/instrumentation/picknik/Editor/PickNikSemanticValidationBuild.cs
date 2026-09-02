// Batch-build entry point copied only into a disposable instrumented project.

using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.Build.Reporting;

public static class PickNikSemanticValidationBuild
{
    public static void BuildAndroid()
    {
        string output = Environment.GetEnvironmentVariable("PICKNIK_VALIDATION_APK");
        if (String.IsNullOrEmpty(output))
        {
            output = Path.GetFullPath(Path.Combine("Builds", "picknik_semantic_validation.apk"));
        }

        string directory = Path.GetDirectoryName(output);
        if (!String.IsNullOrEmpty(directory))
        {
            Directory.CreateDirectory(directory);
        }

        string[] scenes = EditorBuildSettings.scenes
            .Where(scene => scene.enabled)
            .Select(scene => scene.path)
            .ToArray();
        if (scenes.Length == 0)
        {
            throw new InvalidOperationException("No enabled Unity scenes found.");
        }

        BuildPlayerOptions options = new BuildPlayerOptions
        {
            scenes = scenes,
            locationPathName = output,
            target = BuildTarget.Android,
            options = BuildOptions.Development,
        };
        BuildReport report = BuildPipeline.BuildPlayer(options);
        if (report.summary.result != BuildResult.Succeeded)
        {
            throw new InvalidOperationException("PickNik semantic-validation build failed: " + report.summary.result);
        }

        Console.WriteLine("PICKNIK_VALIDATION_APK=" + output);
    }
}
