import "dotenv/config";
export declare const auth: import("better-auth").Auth<{
    database: any;
    secret: string | undefined;
    baseURL: string;
    plugins: [{
        id: "bearer";
        hooks: {
            before: {
                matcher(context: import("better-auth").HookEndpointContext): boolean;
                handler: (inputContext: import("better-call").MiddlewareInputContext<import("better-call").MiddlewareOptions>) => Promise<{
                    context: {
                        headers: Headers;
                    };
                } | undefined>;
            }[];
            after: {
                matcher(context: import("better-auth").HookEndpointContext): true;
                handler: (inputContext: import("better-call").MiddlewareInputContext<import("better-call").MiddlewareOptions>) => Promise<void>;
            }[];
        };
        options: import("better-auth/plugins").BearerOptions | undefined;
    }];
    advanced: {
        useSecureCookies: true;
        defaultCookieAttributes: {
            sameSite: "none";
            secure: true;
        };
    } | undefined;
    emailAndPassword: {
        enabled: true;
        requireEmailVerification: false;
    };
    session: {
        expiresIn: number;
        updateAge: number;
        cookieCache: {
            enabled: true;
            maxAge: number;
        };
    };
    trustedOrigins: string[];
}>;
