TOODs:
done 1. Definitions of service types and how to "stop" each of them;
done 2. Cleanup work after stopping service (final log update, etc.);
done 3. Mark instances as "stopping" and let the background task stop them "for real" (by calling boto3 api);
done 4. Read "service_type" from module object instead of config file;
5. register/DEREGISTER instances even if they're not launched from this app;
done 6. Add page feed back when sending AJAX requests.
done (one) 7. Add API views. (Consider using django REST framework)
8. Register only "ok" instances with ELB;
9. Copy configuration from existing module;
10. API server: return something meaningful;
11. Resolve new instance displayed as "Terminated" issue;
12. Add page to edit instance info manually;

