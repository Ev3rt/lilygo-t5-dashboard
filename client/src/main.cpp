#include <Arduino.h>
#include <Wire.h>
#include <WiFi.h>

#include "epd_driver.h"
#include "roboto12.h"
#include "roboto18.h"

// Screen settings
uint8_t *fb;
int x = 0;
int y = 0;

// WiFi settings
String SSID = "...";
String password = "...";
String host = "...";
uint16_t port = 55556;

// Data
String now = "";

void init_wifi()
{
    WiFi.mode(WIFI_STA);
    WiFi.config(INADDR_NONE, INADDR_NONE, INADDR_NONE, INADDR_NONE);
    WiFi.setHostname("E-Ink Dashboard");
    WiFi.begin(SSID.c_str(), password.c_str());
    Serial.println("Connecting to WiFi...");
    while (WiFi.status() != WL_CONNECTED)
    {
        Serial.println("Waiting for WiFi...");
        delay(1000);
    }
    Serial.println(WiFi.localIP());
}

void invert_header()
{
    for (int i = 0; i < EPD_WIDTH * 32 / 2; i++)
    {
        fb[i] = ~fb[i];
    }
}

void get_data()
{
    WiFiClient client;
    if (!client.connect(host.c_str(), port))
    {
        Serial.println("Connection failed.");
        return;
    }

    int maxloops = 0;

    // wait for the server's reply to become available
    while (!client.available() && maxloops < 100)
    {
        maxloops++;
        delay(10); // delay 1 msec
    }

    while (client.available() > 0)
    {
        // read back one line from the server
        String line = client.readStringUntil(']');
        Serial.println(line);

        int firstSeparator = line.indexOf("|");
        if (firstSeparator != -1)
        {
            String type = line.substring(0, firstSeparator);
            if (type == "TIME")
            {
                now = line.substring(firstSeparator + 1);
                Serial.print("Received date/time: ");
                Serial.println(now);
            }
        }
    }
}

void draw_screen()
{
    // Clear the frame buffer. Colors are 4 bit so a byte contains 2 pixels.
    // 0x0 = black, 0xF = white.
    memset(fb, 0xFF, EPD_WIDTH * EPD_HEIGHT / 2);

    // Enable the screen
    epd_poweron();
    delay(10);
    // Clear the screen
    epd_clear();

    epd_draw_rect(0, EPD_HEIGHT / 2 - 1, EPD_WIDTH - 1, EPD_HEIGHT / 2, 0, fb);
    delay(10);
    epd_draw_rect(EPD_WIDTH / 2 - 1, 0, EPD_WIDTH / 2, EPD_HEIGHT - 1, 0, fb);
    delay(10);
    x = 0;
    y = 30;
    writeln((GFXfont *)&Roboto18, now.c_str(), &x, &y, fb);
    delay(10);

    // Invert the header (time/wifi)
    invert_header();

    // Draw the framebuffer to the screen
    epd_draw_grayscale_image(epd_full_screen(), fb);
    delay(10);

    // Disable the screen
    epd_poweroff();
}

void setup()
{
    // Start serial communication
    Serial.begin(115200);

    // Initialize WiFi
    init_wifi();

    // Initialize e-ink panel
    epd_init();

    // Allocate the frame buffer
    fb = (uint8_t *)ps_calloc(sizeof(uint8_t), EPD_WIDTH * EPD_HEIGHT / 2);
}

void loop()
{
    // Connect to the server and retrieve data
    get_data();

    // Draw the screen
    draw_screen();

    // Sleep for a minute
    delay(60000);
}
