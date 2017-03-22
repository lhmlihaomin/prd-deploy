TOODs:
done 1. Definitions of service types and how to "stop" each of them;
done 2. Cleanup work after stopping service (final log update, etc.);
done 3. Mark instances as "stopping" and let the background task stop them "for real" (by calling boto3 api);
done 4. Read "service_type" from module object instead of config file;
5. register/DEREGISTER instances even if they're not launched from this app;
6. Add page feed back when sending AJAX requests.
