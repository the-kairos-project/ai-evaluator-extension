# main.py
"""
LinkedIn MCP Server - Main application entry point.

Implements a three-phase startup:
1. Authentication Setup Phase - Credential validation and session establishment
2. Driver Management Phase - Chrome WebDriver initialization with LinkedIn login
3. Server Runtime Phase - MCP server startup with transport selection

"""

import logging
import sys
from typing import Literal

import inquirer  # type: ignore
from linkedin_scraper.exceptions import (
    CaptchaRequiredError,
    InvalidCredentialsError,
    LoginTimeoutError,
    RateLimitError,
    SecurityChallengeError,
    TwoFactorAuthError,
)

from linkedin_mcp_server.cli import print_claude_config
from linkedin_mcp_server.config import (
    check_keychain_data_exists,
    clear_all_keychain_data,
    get_config,
    get_keyring_name,
)
from linkedin_mcp_server.drivers.chrome import close_all_drivers, get_or_create_driver
from linkedin_mcp_server.exceptions import CredentialsNotFoundError, LinkedInMCPError
from linkedin_mcp_server.logging_config import configure_logging
from linkedin_mcp_server.server import create_mcp_server, shutdown_handler
from linkedin_mcp_server.setup import run_cookie_extraction_setup, run_interactive_setup

logger = logging.getLogger(__name__)


def choose_transport_interactive() -> Literal["stdio", "streamable-http"]:
    """Prompt user for transport mode using inquirer."""
    questions = [
        inquirer.List(
            "transport",
            message="Choose mcp transport mode",
            choices=[
                ("stdio (Default CLI mode)", "stdio"),
                ("streamable-http (HTTP server mode)", "streamable-http"),
            ],
            default="stdio",
        )
    ]
    answers = inquirer.prompt(questions)

    if not answers:
        raise KeyboardInterrupt("Transport selection cancelled by user")

    return answers["transport"]


def clear_keychain_and_exit() -> None:
    """Clear LinkedIn keychain data and exit."""
    config = get_config()

    # Configure logging
    configure_logging(
        log_level=config.server.log_level,
        json_format=not config.is_interactive and config.server.log_level != "DEBUG",
    )

    # Get version for logging
    version = get_version()

    logger.info(f"LinkedIn MCP Server v{version} - Keychain Clear mode started")

    # Check what exists in keychain
    existing = check_keychain_data_exists()

    # If nothing exists, inform user and exit
    if not existing["has_any"]:
        logger.info("ℹ️  No LinkedIn data found in keychain")
        logger.info("Nothing to clear.")
        sys.exit(0)

    # Show confirmation prompt for existing items only
    keyring_name = get_keyring_name()
    logger.info(f"🔑 Clear LinkedIn data from {keyring_name}?")
    logger.info("This will remove:")

    items_to_remove = []
    if existing["has_credentials"]:
        credential_parts = []
        if existing["has_email"]:
            credential_parts.append("email")
        if existing["has_password"]:
            credential_parts.append("password")
        items_to_remove.append(f"  • LinkedIn {' and '.join(credential_parts)}")

    if existing["has_cookie"]:
        items_to_remove.append("  • LinkedIn session cookie")

    for item in items_to_remove:
        logger.info(item)
    logger.info()

    # Get user confirmation
    try:
        confirmation = (
            input("Are you sure you want to clear this keychain data? (y/N): ")
            .strip()
            .lower()
        )
        if confirmation not in ("y", "yes"):
            logger.info("❌ Operation cancelled")
            sys.exit(0)
    except KeyboardInterrupt:
        logger.info("\n❌ Operation cancelled")
        sys.exit(0)

    try:
        # Clear all keychain data
        success = clear_all_keychain_data()

        if success:
            logger.info("Keychain data cleared successfully")
            logger.info("✅ LinkedIn keychain data cleared successfully!")
        else:
            logger.error("Failed to clear keychain data")
            logger.info("❌ Failed to clear some keychain data - check logs for details")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Error clearing keychain: {e}")
        logger.info(f"❌ Error clearing keychain: {e}")
        sys.exit(1)

    sys.exit(0)


def get_cookie_and_exit() -> None:
    """Get LinkedIn cookie and exit (for Docker setup)."""
    config = get_config()

    # Configure logging
    configure_logging(
        log_level=config.server.log_level,
        json_format=not config.is_interactive and config.server.log_level != "DEBUG",
    )

    # Get version for logging
    version = get_version()

    logger.info(f"LinkedIn MCP Server v{version} - Cookie Extraction mode started")

    try:
        # Run cookie extraction setup
        cookie = run_cookie_extraction_setup()

        logger.info("Cookie extraction successful")
        logger.info("✅ Login successful!")
        logger.info("🍪 LinkedIn Cookie extracted:")
        logger.info(cookie)

        # Try to copy to clipboard
        clipboard_success = False
        try:
            import pyperclip

            pyperclip.copy(cookie)
            clipboard_success = True
            logger.info("📋 Cookie copied to clipboard!")
        except Exception as e:
            logger.debug(f"pyperclip clipboard failed: {e}")

        if not clipboard_success:
            logger.info(
                "💡 Set this cookie as an environment variable in your config or pass it with --cookie flag"
            )

    except Exception as e:
        logger.error(f"Error getting cookie: {e}")

        # Provide specific guidance for security challenges
        error_msg = str(e).lower()
        if "security challenge" in error_msg or "captcha" in error_msg:
            logger.info("❌ LinkedIn security challenge detected")
            logger.info("💡 Try one of these solutions:")
            logger.info(
                "   1. Use an existing LinkedIn cookie from your browser instead (see instructions below)"
            )
            logger.info(
                "   2. Use --no-headless flag (manual installation required, does not work with Docker) and solve the security challenge manually"
            )
            logger.info("\n🍪 To get your LinkedIn cookie manually:")
            logger.info("   1. Login to LinkedIn in your browser")
            logger.info("   2. Open Developer Tools (F12)")
            logger.info("   3. Go to Application/Storage > Cookies > www.linkedin.com")
            logger.info("   4. Copy the 'li_at' cookie value")
            logger.info("   5. Set LINKEDIN_COOKIE environment variable or use --cookie flag")
        elif "invalid credentials" in error_msg:
            logger.info("❌ Invalid LinkedIn credentials")
            logger.info("💡 Please check your email and password")
        else:
            logger.info("❌ Failed to obtain cookie - check your credentials")
        sys.exit(1)

    sys.exit(0)


def ensure_authentication_ready() -> str:
    """
    Phase 1: Ensure authentication is ready before any drivers are created.

    Returns:
        str: Valid LinkedIn session cookie

    Raises:
        CredentialsNotFoundError: If authentication setup fails
    """
    config = get_config()

    # Check if we already have a cookie in config (from keyring, env, or args)
    if config.linkedin.cookie:
        logger.info("Using LinkedIn cookie from configuration")
        return config.linkedin.cookie

    # If in non-interactive mode and no cookie, fail immediately
    if not config.is_interactive:
        raise CredentialsNotFoundError(
            "No LinkedIn cookie found for non-interactive mode. You can:\n"
            "  1. Run with --get-cookie to extract a cookie using email/password\n"
            "  2. Set LINKEDIN_COOKIE environment variable with a valid LinkedIn session cookie"
        )

    # Run interactive setup to get credentials and obtain cookie
    logger.info("Setting up LinkedIn authentication...")
    return run_interactive_setup()


def initialize_driver_with_auth(authentication: str) -> None:
    """
    Phase 2: Initialize driver using existing authentication.

    Args:
        authentication: LinkedIn session cookie

    Raises:
        Various exceptions if driver creation or login fails
    """
    config = get_config()

    if config.server.lazy_init:
        logger.info(
            "Using lazy initialization - driver will be created on first tool call"
        )
        return

    logger.info("Initializing Chrome WebDriver and logging in...")

    try:
        # Create driver and login with provided authentication
        get_or_create_driver(authentication)
        logger.info("✅ Web driver initialized and authenticated successfully")

    except Exception as e:
        logger.error(f"Failed to initialize driver: {e}")
        raise e


def get_version() -> str:
    """Get version from pyproject.toml."""
    try:
        import os
        import tomllib

        pyproject_path = os.path.join(os.path.dirname(__file__), "pyproject.toml")
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)
            return data["project"]["version"]
    except Exception:
        return "unknown"


def main() -> None:
    """Main application entry point with clear phase separation."""

    # Get configuration (this sets config.is_interactive)
    config = get_config()

    # Configure logging FIRST (before any logger usage)
    configure_logging(
        log_level=config.server.log_level,
        json_format=not config.is_interactive and config.server.log_level != "DEBUG",
    )

    # Get version for logging/display
    version = get_version()

    # Only print banner in interactive mode (to avoid interfering with MCP protocol)
    if config.is_interactive:
        logger.info(f"🔗 LinkedIn MCP Server v{version} 🔗")
        logger.info("=" * 40)

    # Always log version (this goes to stderr/logging, not stdout)
    logger.info(f"🔗 LinkedIn MCP Server v{version} 🔗")

    # Handle --clear-keychain flag immediately
    if config.server.clear_keychain:
        clear_keychain_and_exit()

    # Handle --get-cookie flag immediately
    if config.server.get_cookie:
        get_cookie_and_exit()

    logger.debug(f"Server configuration: {config}")

    # Phase 1: Ensure Authentication is Ready
    try:
        authentication = ensure_authentication_ready()
        logger.info("✅ Authentication ready")
        logger.info("Authentication ready")
    except CredentialsNotFoundError as e:
        logger.error(f"Authentication setup failed: {e}")
        if config.is_interactive:
            logger.info(
                "\n❌ Authentication required - please provide LinkedIn's li_at cookie"
            )
        else:
            # TODO: make claude desktop handle this without terminating
            logger.info("\n❌ Cookie required for Docker/non-interactive mode")

        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("\n\n👋 Setup cancelled by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error during authentication setup: {e}")
        logger.info("\n❌ Setup failed - please try again")
        sys.exit(1)

    # Phase 2: Initialize Driver (if not lazy)
    try:
        initialize_driver_with_auth(authentication)
    except InvalidCredentialsError as e:
        logger.error(f"Driver initialization failed with invalid credentials: {e}")

        # Cookie was already cleared in driver layer
        # In interactive mode, try setup again
        if config.is_interactive:
            logger.info(f"\n❌ {str(e)}")
            logger.info("🔄 Starting interactive setup for new authentication...")
            try:
                new_authentication = run_interactive_setup()
                # Try again with new authentication
                initialize_driver_with_auth(new_authentication)
                logger.info("✅ Successfully authenticated with new credentials")
            except Exception as setup_error:
                logger.error(f"Setup failed: {setup_error}")
                logger.info(f"\n❌ Setup failed: {setup_error}")
                sys.exit(1)
        else:
            logger.info(f"\n❌ {str(e)}")
            if not config.server.lazy_init:
                sys.exit(1)
    except (
        LinkedInMCPError,
        CaptchaRequiredError,
        SecurityChallengeError,
        TwoFactorAuthError,
        RateLimitError,
        LoginTimeoutError,
    ) as e:
        logger.error(f"Driver initialization failed: {e}")
        logger.info(f"\n❌ {str(e)}")
        if not config.server.lazy_init:
            sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error during driver initialization: {e}")
        logger.info(f"\n❌ Driver initialization failed: {e}")
        if not config.server.lazy_init:
            sys.exit(1)

    # Phase 3: Server Runtime
    try:
        # Decide transport using the new config system
        transport = config.server.transport

        # Only show transport prompt if:
        # a) running in interactive environment AND
        # b) transport wasn't explicitly set via CLI/env
        if config.is_interactive and not config.server.transport_explicitly_set:
            logger.info("\n🚀 Server ready! Choose transport mode:")
            transport = choose_transport_interactive()
        elif not config.is_interactive and not config.server.transport_explicitly_set:
            # If non-interactive and no transport explicitly set, use default (stdio)
            transport = config.server.transport

        # Print configuration for Claude if in interactive mode and using stdio transport
        if config.is_interactive and transport == "stdio":
            print_claude_config()

        # Create and run the MCP server
        mcp = create_mcp_server()

        # Start server
        logger.info(f"\n🚀 Running LinkedIn MCP server ({transport.upper()} mode)...")
        if transport == "streamable-http":
            logger.info(
                f"📡 HTTP server will be available at http://{config.server.host}:{config.server.port}{config.server.path}"
            )
            mcp.run(
                transport=transport,
                host=config.server.host,
                port=config.server.port,
                path=config.server.path,
            )
        else:
            mcp.run(transport=transport)

    except KeyboardInterrupt:
        logger.info("\n⏹️  Server stopped by user")
        exit_gracefully(0)
    except Exception as e:
        logger.error(f"Server runtime error: {e}")
        logger.info(f"\n❌ Server error: {e}")
        exit_gracefully(1)


def exit_gracefully(exit_code: int = 0) -> None:
    """Exit the application gracefully, cleaning up resources."""
    logger.info("👋 Shutting down LinkedIn MCP server...")

    # Clean up drivers
    close_all_drivers()

    # Clean up server
    shutdown_handler()

    sys.exit(exit_code)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        exit_gracefully(0)
    except Exception as e:
        logger.error(
            f"Error running MCP server: {e}",
            extra={"exception_type": type(e).__name__, "exception_message": str(e)},
        )
        logger.info(f"❌ Error running MCP server: {e}")
        exit_gracefully(1)
