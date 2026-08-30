module shared(input a,b,c,d, output y); wire t=a^b; assign y=(t&c)|(t&d); endmodule
